# -*- coding: utf-8 -*-

# /usr/share/qgis/python/plugins/processing/script/ScriptTemplate.py
# https://anitagraser.com/2018/03/25/processing-script-template-for-qgis3/
# https://qgis.org/pyqgis/3.0/index.html

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import ( QgsField, 
                        QgsFeature, 
                        QgsFeatureSink, 
                        QgsFeatureRequest, 
                        QgsProcessing, 
                        QgsProcessingAlgorithm, 
                        QgsProcessingParameterFeatureSource, 
                        QgsProcessingParameterFeatureSink, 
                        QgsProcessingException, 
                        QgsProcessingParameterField, 
                        QgsProcessingParameterNumber, 
                        QgsProcessingParameterBoolean, 
                        QgsFields,
                        QgsGeometry,
                        QgsRectangle,
                        QgsWkbTypes)
from math import ceil

# useful fonction
center_of = lambda a, b : a + (b - a) / 2.0


__author__ = 'oSvy'
__date__ = 'September 2018'
__copyright__ = '(C) 2018, oSvy'
__revision__ = '$Format:%H$'

# application parameters
HELP_TEXT = """
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

"""

NAME_TEXT = 'minimum coverage grid'
SHORT_NAME_TEXT = 'mCG'
DISPLAY_NAME_TEXT = 'Minimum coverage grid'
GROUP_TEXT = 'grid'
GROUPID_TEXT = 'grid'

SLAB_DX_DEFAULT = 7000
SLAB_DX_MIN = 10
SLAB_DY_DEFAULT = 6000
SLAB_DY_MIN = 10
OVERLAP_DEFAULT = 0
OVERLAP_MIN = 0
OVERLAP_MAX = 40
GAP_DEFAULT = 0
GAP_MIN = 0
GAP_MAX = 10

# error messages
FIELD_EXISTS_ERR = '\n\nThe "{}" column already exists, change the script code or column name in input table'

class MinimumCoverGrid(QgsProcessingAlgorithm):
    """
    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.
    INPUT = 'input table'
    ORD_FIELD = 'sort column'
    SLAB_DX = 'slab\'s width'
    SLAB_DY = 'slab\'s height'
    OVERLAP = 'buffer percentage around objects'
    SLAB_BOUND = 'add columns containing coordinates of slabs'
    OBJECT_BOUND = 'add columns containing coordinates of bounding boxes'
    NO_BLANK = 'do not keep "white" slabs'
    GAP = 'number of offset attempts to be applied to try to obtain a minimum of slabs (slow!)'
    OUTPUT = 'minimum coverage grid'

    def __init__(self): 
        super().__init__()

    def helpUrl(self): 
        return "https://qgis.org"

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate(SHORT_NAME_TEXT, string)

    def createInstance(self):
        return MinimumCoverGrid()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return NAME_TEXT

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(DISPLAY_NAME_TEXT)

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(GROUP_TEXT)

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return GROUPID_TEXT

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr(HELP_TEXT)

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, 
            self.tr(self.INPUT),
            [QgsProcessing.TypeVectorAnyGeometry]))
        self.addParameter(QgsProcessingParameterField(
            self.ORD_FIELD, 
            self.tr(self.ORD_FIELD),
            parentLayerParameterName=self.INPUT,
            optional=True))
        self.addParameter(QgsProcessingParameterNumber(
            self.SLAB_DX, 
            self.tr(self.SLAB_DX), 
            QgsProcessingParameterNumber.Integer,  
            SLAB_DX_DEFAULT,
            False, 
            SLAB_DX_MIN))
        self.addParameter(QgsProcessingParameterNumber(
            self.SLAB_DY, 
            self.tr(self.SLAB_DY), 
            QgsProcessingParameterNumber.Integer,  
            SLAB_DY_DEFAULT,
            False, 
            SLAB_DY_MIN))
        self.addParameter(QgsProcessingParameterNumber(
            self.OVERLAP, 
            self.tr(self.OVERLAP), 
            QgsProcessingParameterNumber.Integer,  
            OVERLAP_DEFAULT,
            False, 
            OVERLAP_MIN,
            OVERLAP_MAX))
        self.addParameter(QgsProcessingParameterBoolean(
            self.SLAB_BOUND, 
            self.tr(self.SLAB_BOUND), 
            False, 
            False))
        self.addParameter(QgsProcessingParameterBoolean(
            self.OBJECT_BOUND, 
            self.tr(self.OBJECT_BOUND), 
            False, 
            False))
        self.addParameter(QgsProcessingParameterBoolean(
            self.NO_BLANK, 
            self.tr(self.NO_BLANK), 
            False, 
            False))
        self.addParameter(QgsProcessingParameterNumber(
            self.GAP, 
            self.tr(self.GAP), 
            QgsProcessingParameterNumber.Integer,  
            GAP_DEFAULT,
            False, 
            GAP_MIN,
            GAP_MAX))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, 
            self.tr(self.OUTPUT),
            QgsProcessing.TypeVectorPolygon,
            optional=True))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        # retrieve parameters
        source = self.parameterAsSource(parameters, self.INPUT, context)
        ord_field = self.parameterAsFields(parameters, self.ORD_FIELD ,context)
        slab_dx = self.parameterAsInt(parameters, self.SLAB_DX, context)
        slab_dy = self.parameterAsInt(parameters, self.SLAB_DY, context)
        overlap = self.parameterAsInt(parameters, self.OVERLAP, context)
        slab_bound = self.parameterAsBool(parameters, self.SLAB_BOUND, context)
        object_bound = self.parameterAsBool(parameters, self.OBJECT_BOUND, context)
        no_blank = self.parameterAsBool(parameters, self.NO_BLANK, context)
        gap = self.parameterAsInt(parameters, self.GAP, context)

        # If source was not found, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSourceError method to return a standard
        # helper text for when a source cannot be evaluated
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        # extra fields definition
        grid_fields = QgsFields()
        additional_attributes = ('_id_object', '_id_slab', '_id_object_slab', '_row_object_slab', '_col_object_slab')
        additional_attributes_ord = ('_ord_object_slab',) if ord_field else ()
        additional_attributes_slab_bound = ('_min_x_slab', '_max_x_slab', '_min_y_slab', '_max_y_slab') if slab_bound else ()
        additional_attributes_object_bound = ('_min_x_object', '_max_x_object', '_min_y_object', '_max_y_object') if object_bound else ()
        for f in source.fields():
            grid_fields.append(f)
            field_name = f.name()
            # raise if original fields exist with the same name
            if (field_name in additional_attributes) or \
               (field_name in additional_attributes_ord) or \
               (field_name in additional_attributes_slab_bound) or \
               (field_name in additional_attributes_object_bound):
                raise QgsProcessingException(self.tr(FIELD_EXISTS_ERR.format(field_name)))
        # add extra fields
        for attr in additional_attributes:
            grid_fields.append(QgsField(attr, QVariant.Int))
        for attr in additional_attributes_ord:
            grid_fields.append(QgsField(attr, QVariant.String))
        for attr in additional_attributes_slab_bound:
            grid_fields.append(QgsField(attr, QVariant.Double))
        for attr in additional_attributes_object_bound:
            grid_fields.append(QgsField(attr, QVariant.Double))

        (sink, dest_id) = self.parameterAsSink(parameters, 
                                                self.OUTPUT, 
                                                context,
                                                grid_fields, 
                                                QgsWkbTypes.Polygon, 
                                                source.sourceCrs())

        # If sink was not created, throw an exception to indicate that the algorithm
        # encountered a fatal error. The exception text can be any string, but in this
        # case we use the pre-built invalidSinkError method to return a standard
        # helper text for when a sink cannot be evaluated
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        # Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures()
        current_slab = 0
        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            # Update the progress bar
            feedback.setProgress(int(current * total))

            # Compute bounding box
            bounding_geom = feature.geometry().boundingBox()
            min_x_object = bounding_geom.xMinimum()
            max_x_object = bounding_geom.xMaximum()
            min_y_object = bounding_geom.yMinimum()
            max_y_object = bounding_geom.yMaximum()
            if overlap > 0:        # if a buffer must extend object
                buffer_geom = feature.geometry().buffer(overlap / 100.0 * max((max_x_object - min_x_object), (max_y_object - min_y_object)), 10)
            else:                  # get the feature bounding box
                buffer_geom = feature.geometry()

            # slabs dimensions
            object_dx = max_x_object - min_x_object
            object_dy = max_y_object - min_y_object
            slab_count_x = max(1, int(ceil(object_dx / slab_dx)))
            slab_count_y = max(1, int(ceil(object_dy / slab_dy)))
            center_x = center_of(min_x_object, max_x_object)
            center_y = center_of(min_y_object, max_y_object)
            minimum_x_center = center_x - slab_dx * slab_count_x / 2.0
            minimum_y_center = center_y - slab_dy * slab_count_y / 2.0
            max_margin_x = slab_count_x * slab_dx - object_dx
            max_margin_y = slab_count_y * slab_dy - object_dy

            # so as not to move the slabs out of the bounding of the buffered object when calculating the grid moved to limit
            shift_limit_x = lambda x : -max_margin_x / 2.0 if x < -max_margin_x / 2.0 else x if x < max_margin_x / 2.0 else max_margin_x / 2.0
            shift_limit_y = lambda y : -max_margin_y / 2.0 if y < -max_margin_y / 2.0 else y if y < max_margin_y / 2.0 else max_margin_y / 2.0

            # can we try to optimize the number of slabs?
            if slab_count_x * slab_count_y <= 2 or gap == 0: # no optimization possible or desired
                minimum_ajustment_x_step = 0
                minimum_ajustment_y_step = 0
                gap_x = 0
                gap_y = 0
            else:
                # the number of possible offsets is calculated, rounded up to reach the limit
                half_max_shift_number_x = gap
                half_max_shift_number_y = gap
                gap_x = int(ceil(max_margin_x / 2.0 / gap))
                gap_y = int(ceil(max_margin_y / 2.0 / gap))

                # minimum number of slabs intersecting the object
                minimum_slab_count = slab_count_x * slab_count_y
                minimum_ajustment_x_step = 0
                minimum_ajustment_y_step = 0
                minimum_balance = 0

                # all possible shifts
                for ajustment_x_step in range(-gap, gap + 1):
                    for ajustment_y_step in range(-gap, gap + 1):
                        intersect_number = 0

                        # search for all slabs if they intersect the buffer
                        for slab_x in range(slab_count_x):
                            for slab_y in range(slab_count_y):
                                rectangle = QgsGeometry.fromRect( \
                                                QgsRectangle( \
                                                    minimum_x_center + slab_x * slab_dx + shift_limit_x(ajustment_x_step * gap_x), \
                                                    minimum_y_center + slab_y * slab_dy + shift_limit_y(ajustment_y_step * gap_y), \
                                                    minimum_x_center + (slab_x + 1) * slab_dx + shift_limit_x(ajustment_x_step * gap_x), \
                                                    minimum_y_center + (slab_y + 1) * slab_dy + shift_limit_y(ajustment_y_step * gap_y)))

                                if rectangle.intersects(buffer_geom):
                                    intersect_number += 1

                        # keep the first minimal value close to the average distance
                        balance = (ajustment_x_step * gap_x)**2 + (ajustment_y_step * gap_y)**2
                        if intersect_number < minimum_slab_count or balance < minimum_balance:
                            minimum_slab_count = intersect_number
                            minimum_ajustment_x_step = ajustment_x_step
                            minimum_ajustment_y_step = ajustment_y_step
                            minimum_balance = balance

            # we found the position of the slabs, we can now create the grid for this object
            id_object_slab = 0
            row_object_slab = 0
            for slab_x in range(slab_count_x):
                row_object_slab += 1
                col_object_slab = 0
                for slab_y in range(slab_count_y):
                    col_object_slab += 1
                    # the slab
                    min_x_slab = minimum_x_center + slab_x * slab_dx + shift_limit_x(minimum_ajustment_x_step * gap_x)
                    min_y_slab = minimum_y_center + slab_y * slab_dy + shift_limit_y(minimum_ajustment_y_step * gap_y)
                    max_x_slab = minimum_x_center + (slab_x + 1) * slab_dx + shift_limit_x(minimum_ajustment_x_step * gap_x)
                    max_y_slab = minimum_y_center + (slab_y + 1) * slab_dy + shift_limit_y(minimum_ajustment_y_step * gap_y)
                    rectangle = QgsGeometry.fromRect(QgsRectangle(min_x_slab, min_y_slab, max_x_slab, max_y_slab))

                    # intersection with the buffer
                    if not no_blank or (no_blank and rectangle.intersects(buffer_geom)):
                        current_slab += 1
                        id_object_slab += 1
                        output_feature = QgsFeature()
                        output_feature.setGeometry(rectangle)
                        # original attributs
                        attribute_values = feature.attributes()[:]                                              
                        # extra fields
                        attribute_values.extend([current, current_slab, id_object_slab, row_object_slab, col_object_slab]) 
                        # sort field
                        if ord_field:
                            attribute_values.append('{}#{:04d}'.format(feature[ord_field[0]], id_object_slab))     
                        # slab's coordinates
                        if slab_bound:
                            attribute_values.extend([min_x_slab, max_x_slab, min_y_slab, max_y_slab])           
                        # bounding box
                        if object_bound:
                            attribute_values.extend([min_x_object, max_x_object, min_y_object, max_y_object])           

                        # add fields and geom
                        output_feature.setAttributes(attribute_values)
                        sink.addFeature(output_feature, QgsFeatureSink.FastInsert)

        return {self.OUTPUT: dest_id}

# That's all folks!
