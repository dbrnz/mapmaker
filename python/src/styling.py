#===============================================================================
#
#  Flatmap viewer and annotation tools
#
#  Copyright (c) 2019  David Brooks
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#===============================================================================

import json

#===============================================================================

PAINT_STYLES = {
    'background-opacity': 0.4,
    'fill-color': '#c0c0c0',
    'fill-outline-color': '#f0f',
    'fill-opacity': 0.7,
    'border-stroke-color': '#0f0',
    'border-stroke-width': 1,
    'line-stroke-color': '#f00',
    'line-stroke-width': 2,
}

#===============================================================================
#===============================================================================

class ImageLayer(object):
    @staticmethod
    def style(id, source_id):
        return {
            'id': id,
            'source': source_id,
            'type': 'raster',
            'paint': {
                'raster-opacity': PAINT_STYLES['background-opacity']
            }
        }

#===============================================================================
#===============================================================================

class FeatureLayer(object):
    @staticmethod
    def style(source_id, layer_id,
            fill_colour=PAINT_STYLES['fill-color'],
            line_colour=PAINT_STYLES['line-stroke-color'],
            line_width=PAINT_STYLES['line-stroke-width']):
        return [
            FeatureFillLayer.style('{}-fill'.format(layer_id), source_id, layer_id, fill_colour),
            FeatureBorderLayer.style('{}-border'.format(layer_id), source_id, layer_id),
            FeatureLineLayer.style('{}-line'.format(layer_id), source_id, layer_id, line_colour, line_width)
        ]

#===============================================================================

class FeatureFillLayer(object):
    @staticmethod
    def style(id, source_id, layer_id, fill_colour=PAINT_STYLES['fill-color']):
        return {
            'id': id,
            'source': source_id,
            'source-layer': layer_id,
            'type': 'fill',
            'filter': [
                '==',
                '$type',
                'Polygon'
            ],
            'paint': {
                'fill-color': fill_colour,
                'fill-outline-color': PAINT_STYLES['fill-outline-color'],
                'fill-opacity': PAINT_STYLES['fill-opacity']
            }
        }

#===============================================================================

class FeatureBorderLayer(object):
    @staticmethod
    def style(id, source_id, layer_id):
        return {
            'id': id,
            'source': source_id,
            'source-layer': layer_id,
            'type': 'line',
            'filter': [
                '==',
                '$type',
                'Polygon'
            ],
            'paint': {
                'line-color': PAINT_STYLES['border-stroke-color'],
                'line-width': PAINT_STYLES['border-stroke-width']
            }
        }

#===============================================================================

class FeatureLineLayer(object):
    @staticmethod
    def style(id, source_id, layer_id,
            line_colour=PAINT_STYLES['line-stroke-color'],
            line_width = PAINT_STYLES['line-stroke-width']):
        return {
            'id': id,
            'source': source_id,
            'source-layer': layer_id,
            'type': 'line',
            'filter': [
                '==',
                '$type',
                'LineString'
            ],
            'paint': {
                'line-color': line_colour,
                'line-width': line_width
            }
        }

#===============================================================================
#===============================================================================

class BackgroundSource(object):
    @staticmethod
    def style(base_url, background_image, bounds):
        return {
            'type': 'image',
            'url': '{}/images/{}'.format(base_url, background_image),
            'coordinates': [
                [bounds[0], bounds[3]],
                [bounds[2], bounds[3]],
                [bounds[2], bounds[1]],
                [bounds[0], bounds[1]]
            ]
        }

#===============================================================================

class FeaturesSource(object):
    @staticmethod
    def style(base_url, layer_dict, bounds):
        return {
            'type': 'vector',
            'tiles': ['{}/mvtiles/{{z}}/{{x}}/{{y}}'.format(base_url)],
            'format': 'pbf',
            'version': '2',
            'minzoom': 0,
            'maxzoom': 14,
            'bounds': bounds,
            'attribution': '© Auckland Bioengineering Institute',
            'generator': 'tippecanoe v1.34.0',
            'vector_layers': layer_dict['vector_layers'],
            'tilestats': layer_dict['tilestats']
        }

#===============================================================================
#===============================================================================

class Sources(object):
    @staticmethod
    def style(base_url, background_id, background_image, features_id, layer_dict, bounds):
        return {
            background_id: BackgroundSource.style(base_url, background_image, bounds),
            features_id: FeaturesSource.style(base_url, layer_dict, bounds),
        }

#===============================================================================

class Layers(object):
    @staticmethod
    def style(background_id, features_id, layer_dict):
        layers = []
        layers.append(ImageLayer.style('background', background_id))
        for layer in layer_dict['vector_layers']:
            layers.extend(FeatureLayer.style(features_id, layer['id']))
        return layers

#===============================================================================
#===============================================================================

class Style(object):
    @staticmethod
    def style(base_url, metadata, background_image=None):
        layer_dict = json.loads(metadata['json'])
        background_id = 'background'
        features_id = 'features'
        bounds = [float(x) for x in metadata['bounds'].split(',')]
        return {
            'version': 8,
            'sources': Sources.style(base_url, background_id, background_image, features_id, layer_dict, bounds),
            'zoom': 4,
            'center': [float(x) for x in metadata['center'].split(',')],
            'layers': Layers.style(background_id, features_id, layer_dict)
        }

#===============================================================================
