#===============================================================================
#
# Code (as Javascript) came from
# https://stackoverflow.com/questions/43953138/significant-error-when-approximating-elliptical-arcs-with-bezier-curves-on-canva
# which was based on https://mortoray.com/2017/02/16/rendering-an-svg-elliptical-arc-as-bezier-curves/
#
# Original paper is at http://www.spaceroots.org/documents/ellipse/elliptical-arc.pdf
#
#===============================================================================

import collections
import math

tuple2 = collections.namedtuple('tuple2', 'x y')

#===============================================================================

def clamp(value, min_value, max_value):
#======================================
    return min(max(value, min_value), max_value)

def svg_angle(u, v):
#===================
    dot = u.x*v.x + u.y*v.y
    length = math.sqrt(u.x**2 + u.y**2)*math.sqrt(v.x**2 + v.y**2)
    angle = math.acos(clamp(dot/length, -1, 1))
    if (u.x*v.y - u.y*v.x) < 0:
        angle = -angle
    return angle

def elliptic_arc_point(c, r, phi, eta):
#======================================
    return tuple2(x = c.x + r.x*math.cos(phi)*math.cos(eta) - r.y*math.sin(phi)*math.sin(eta),
                  y = c.y + r.x*math.sin(phi)*math.cos(eta) + r.y*math.cos(phi)*math.sin(eta))

def elliptic_arc_derivative(r, phi, eta):
#========================================
    return tuple2(x = -r.x*math.cos(phi)*math.sin(eta) - r.y*math.sin(phi)*math.cos(eta),
                  y = -r.x*math.sin(phi)*math.sin(eta) + r.y*math.cos(phi)*math.cos(eta))

def cubic_bezier_control_points(c, r, phi, eta1, eta2):
#======================================================
    alpha = math.sin(eta2 - eta1)*(math.sqrt(4 + 3*math.pow(math.tan((eta2 - eta1)/2), 2)) - 1)/3
    P1 = elliptic_arc_point(c, r, phi, eta1)
    d1 = elliptic_arc_derivative(r, phi, eta1)
    Q1 = tuple2(P1.x + alpha*d1.x, P1.y + alpha*d1.y)
    P2 = elliptic_arc_point(c, r, phi, eta2)
    d2 = elliptic_arc_derivative(r, phi, eta2)
    Q2 = tuple2(P2.x - alpha*d2.x, P2.y - alpha*d2.y)
    return (P1, Q1, Q2, P2)

def cubic_bezier_points(r, phi, flagA, flagS, p1, p2):
#====================================================
    r_abs = tuple2(abs(r.x), abs(r.y))
    d = tuple2((p1.x - p2.x), (p1.y - p2.y))
    p = tuple2(math.cos(phi)*d.x/2 + math.sin(phi)*d.y/2,
              -math.sin(phi)*d.x/2 + math.cos(phi)*d.y/2)
    p_sq = tuple2(p.x**2, p.y**2)
    r_sq = tuple2(r_abs.x**2, r_abs.y**2)

    ratio = p_sq.x/r_sq.x + p_sq.y/r_sq.y
    if ratio > 1:
        scale = math.sqrt(ratio)
        r_abs = tuple2(scale*r_abs.x, scale*r_abs.y)
        r_sq = tuple2(r_abs.x**2, r_abs.y**2)

    dq = r_sq.x*p_sq.x + r_sq.y*p_sq.x
    pq = (r_sq.x*r_sq.y - dq)/dq
    q = math.sqrt(max(0, pq))
    if flagA == flagS:
        q = -q

    cp = tuple2(q * r_abs.x*p.y/r_abs.y,
               -q * r_abs.y*p.x/r_abs.x)
    c = tuple2(cp.x*math.cos(phi) - cp.y*math.sin(phi) + (p1.x + p2.x)/2.0,
               cp.x*math.sin(phi) + cp.y*math.cos(phi) + (p1.y + p2.y)/2.0)

    lambda1 = svg_angle(tuple2(                   1,                     0),
                        tuple2((p.x - cp.x)/r_abs.x, ( p.y - cp.y)/r_abs.y))
    delta = svg_angle(tuple2(( p.x - cp.x)/r_abs.x, ( p.y - cp.y)/r_abs.y),
                      tuple2((-p.x - cp.x)/r_abs.x, (-p.y - cp.y)/r_abs.y))
    delta = delta - 2*math.pi*math.floor(delta/(2*math.pi))
    if not flagS:
        delta -= 2*math.pi
    lambda2 = lambda1 + delta

    t = lambda1
    dt = math.pi/4
    curves = []
    while (t + dt) < lambda2:
        curves.append(cubic_bezier_control_points(c, r_abs, phi, t, t + dt))
        t += dt
    curves.append(cubic_bezier_control_points(c, r_abs, phi, t, lambda2))
    return curves

#===============================================================================

if __name__ == '__main__':
    rx = 25
    ry = 100
    phi = -30
    fa = 0
    fs = 1
    x = 100
    y = 200
    x1 = 150
    y1 = 175

    cps = cubic_bezier_points(tuple2(rx, ry), phi*math.pi/180, fa, fs, tuple2(x, y), tuple2(x1, y1))

    for bz in cps:
        print(cps)

#===============================================================================
