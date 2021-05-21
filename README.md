# coverage-layer
***************************************************************************
    minimum_coverage_grid.py
    ------------------------
    Date                 : October 2018
    Copyright            : (C) 2018 by oSvy
    Email                :
 minimum coverage grid
======================

    /***************************************************************************
     *                                                                         *
     *   This program is free software; you can redistribute it and/or modify  *
     *   it under the terms of the GNU General Public License as published by  *
     *   the Free Software Foundation; either version 2 of the License, or     *
     *   (at your option) any later version.                                   *
     *                                                                         *
     ***************************************************************************/

This script aims to facilitate QGIS atlas's use
-----------------------------------------------

Sometimes we want to print on a defined scale objects that are larger than the paper medium.

They must therefore be spread over several slabs.

For each object, the script calculates the bounding box, then computes the minimal slabs' number, and finaly centers the slabs around the object.

It creates a layer of rectangular polygons that cover each objects of a given layer as a parameter.

Rectangular polygons (slabs) have a fixed size given as parameter.

An extent percentage around each object's bounding box may be applied before calculating the slabs.

The produced layer keeps original layer's columns and adds additional columns. If there is a column name conflict, if the script tries to create a column that already exists, it stops.

The additional attributes are:
- '_id_object' an integer for each original object
- '_id_slab' a single integer per slab
- '_id_object_slab' a single integer per slab for each '_id_object'
- '_row_object_slab' the slab's row for each '_id_object'
- '_col_object_slab' the slab's column for each '_id_object'

If a sort column is asked, this attribute is added:
- '_ord_object_slab' a sort value composed of the selected field, an anchor (#) and the single integer per slab for each '_id_object'

If slab's coordinates are asked, these attributes are added:
- '_min_x_slab' a double for the minimum x value
- '_max_x_slab' a double for the maximum x value
- '_min_y_slab' a double for the minimum y value
- '_max_y_slab' a double for the maximum y value

If original object's bounding box's coordinates are asked, these attributes are added:
- '_min_x_object' a double for the minimum x value
- '_max_x_object' a double for the maximum x value
- '_min_y_object' a double for the minimum y value
- '_max_y_object' a double for the maximum y value

Two other options can be chosen:
- You can only keep boxes that intersect the object.
- The set of slabs can be adjusted to the bounding box, but more often it is larger. The algorithm may try to shift the slab around the center to find a smaller number of intersecting slabs.

