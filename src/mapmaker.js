#!/usr/bin/env node
/******************************************************************************

Flatmap viewer and annotation tool

Copyright (c) 2019  David Brooks

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

******************************************************************************/

'use strict';

//==============================================================================

const fs = require('fs');
const path = require('path');

const sizeOf = require('image-size');
const Jimp = require('jimp');
const puppeteer = require('puppeteer');

//==============================================================================

const cropImage = require('./cropimage');

//==============================================================================

const TILE_PIXEL_SIZE = [256, 256];

//==============================================================================

async function svgToPng(svgBase64, svgExtent, imageSize)
{
    const canvas = document.createElement('canvas');
    canvas.width = imageSize[0];
    canvas.height = imageSize[1];

    const ctx = canvas.getContext('2d');

    // Set transparent background
    ctx.fillStyle = '#00FF00FF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    const img = new Image();
    document.body.appendChild(img);

    return new Promise((resolve, reject) =>
    {
        const onLoad = () =>
        {
            ctx.drawImage(img, svgExtent[0], svgExtent[1], svgExtent[2], svgExtent[3],
                               0, 0, imageSize[0], imageSize[1]);
            const dataURI = canvas.toDataURL('image/png');
            document.body.removeChild(img);
            resolve(dataURI);
        }

        const onError = (e) =>
        {
          document.body.removeChild(img);
          reject(`ERROR: ${e}`);
        }

        img.addEventListener("load", onLoad);
        img.addEventListener("error", onError);
        img.src = `data:image/svg+xml;base64,${svgBase64}`;
    });
}

//==============================================================================

class MapMaker
{
	constructor(map, outputDirectory)
	{
        this._map = map;
		this._tileDims = [Math.ceil(this._map.size[0]/TILE_PIXEL_SIZE[0]),
                          Math.ceil(this._map.size[1]/TILE_PIXEL_SIZE[1])];
        this._tiledSize = [TILE_PIXEL_SIZE[0]*this._tileDims[0],
                           TILE_PIXEL_SIZE[1]*this._tileDims[1]];
        const maxTileDim = Math.max(this._tileDims[0], this._tileDims[1]);
        this._fullZoom = Math.ceil(Math.log2(maxTileDim));
		this._outputDirectory = outputDirectory;
	}

    /**
     * Read a SVG file.
     *
     * @param      {String}   svgPath  The path of the SVG file.
     * @return     {Promise}  A Promise resolving to a Buffer.
     */
    async readSvgAsBuffer_(svgPath)
    {
        return new Promise((resolve, reject) => {
            fs.readFile(svgPath, (err, data) => {
                if (err) reject(err)
                else resolve(data);
            })
        });
    }

    async tileZoomLevel_(layer, zoomLevel, svgBuffer, svgExtent, imageSize, page)
    {
        const zoomScale = 2**(this._fullZoom - zoomLevel);
        const zoomedSize = [imageSize[0]/zoomScale, imageSize[1]/zoomScale];

        const pngDataURI = await page.evaluate(svgToPng, svgBuffer.toString('base64'), svgExtent, zoomedSize);

        const pngImage = await Jimp.create(Buffer.from(pngDataURI.substr('data:image/png;base64,'.length), 'base64'));

        const origin = layer.origin ? [layer.origin[0]/zoomScale, layer.origin[1]/zoomScale]
                                    : [0, 0];

        const xTileStart = Math.floor(origin[0]/TILE_PIXEL_SIZE[0]);
        const xStart = xTileStart*TILE_PIXEL_SIZE[0] - origin[0];

        const yTileStart = Math.floor(origin[1]/TILE_PIXEL_SIZE[1]);
        const yStart = zoomedSize[1] + origin[1] - yTileStart*TILE_PIXEL_SIZE[1] - TILE_PIXEL_SIZE[1];

        // Create tiles and write them out

        const tilePromises = [];
        for (let x = xTileStart, xOffset = xStart;
             xOffset < zoomedSize[0];
             x +=1, xOffset += TILE_PIXEL_SIZE[0]) {

            const tileDirectory = path.join(this._outputDirectory, layer.id, `${zoomLevel}`, `${x}`);
            let dirExists = fs.existsSync(tileDirectory);

            for (let y = yTileStart, yOffset = yStart;
                 yOffset > -TILE_PIXEL_SIZE[1];
                 y +=1, yOffset -= TILE_PIXEL_SIZE[1]) {

                const tile = await cropImage.cropImage(pngImage, xOffset, yOffset,
                                                       TILE_PIXEL_SIZE[0], TILE_PIXEL_SIZE[1]);
                if (tile.hasAlpha()) {
                    if (!dirExists) {
                        fs.mkdirSync(tileDirectory, {recursive: true, mode: 0o755});
                        dirExists = true;
                    }
                    tilePromises.push(tile.writeAsync(path.join(tileDirectory, `${y}.png`)));
                }
            }
        }

        return Promise.all(tilePromises);
    }

    async tileLayer_(layer, browser)
    {
        console.log('Tiling', layer.id);

        const svgBuffer = await this.readSvgAsBuffer_(layer.source);

        let svgExtent = layer.sourceExtent;
        if (!svgExtent) {
            const dimensions = sizeOf(svgBuffer);
            svgExtent = [0, 0, dimensions.width, dimensions.height];
        }

        let imageSize = this._map.size;
        if (layer.resolution) {
            imageSize = [layer.resolution*svgExtent[2], layer.resolution*svgExtent[3]];
        }

        const page = await browser.newPage();
        page.on('console', msg => console.log(`Layer ${layer.id}:`, msg.text()));

        // Tile all zoom levels in the layer

        const zoomPromises = [];
        const zoomRange = layer.zoom || [0, this._fullZoom];
        for (let z = zoomRange[0]; z <= zoomRange[1]; z += 1) {
            zoomPromises.push(this.tileZoomLevel_(layer, z, svgBuffer, svgExtent, imageSize, page));
        }
        await Promise.all(zoomPromises);
    }

    async makeTiles()
    {
        const browser = await puppeteer.launch({args: ['--no-sandbox', '--disable-dev-shm-usage']});

        // Tile all layers

        const layerPromises = [];

        for (const layer of this._map.layers) {
            layerPromises.push(this.tileLayer_(layer, browser));
        }

        // Wait for layer tiling complete

        await Promise.all(layerPromises);

        // Then close the browser

        await browser.close();
    }
}

//==============================================================================

function main()
{
	if (process.argv.length < 4) {
	  	console.error('Usage: mapmaker SPECIFICATION OUTPUT_DIRECTORY');
  		process.exit(-1);
	}

	const specification = process.argv[2];
 	if (!fs.existsSync(path.resolve(specification))) {
	  	console.error(`File '${specification} does not exist`);
  		process.exit(-1);
  	}
    const specDir = path.dirname(path.resolve(specification));

	const outputDirectory = process.argv[3];
 	if (!fs.existsSync(path.resolve(outputDirectory))) {
	  	console.error(`Directory '${outputDirectory} does not exist`);
  		process.exit(-1);
  	}

	const map = JSON.parse(fs.readFileSync(specification));

	for (const layer of map.layers) {
        // Relative paths wrt the specification file's directory
        if (!path.isAbsolute(layer.source)) {
            layer.source = path.resolve(specDir, layer.source);
        }
	 	if (!fs.existsSync(path.resolve(layer.source))) {
		  	console.error(`SVG file '${layer.source} does not exist`);
	  		process.exit(-1);
	  	}
	}

	const mapMaker = new MapMaker(map, outputDirectory);

	try {
        mapMaker.makeTiles();
	} catch (e) {
		console.error(e.message);
	}
}

//==============================================================================

main();

//==============================================================================
