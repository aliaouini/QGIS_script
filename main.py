"""
Model exported as python.
Name : mymodel2
Group : 
With QGIS : 32602
"""
from qgis.core import (QgsVectorFileWriter, QgsVectorLayer)

from qgis.core import QgsProcessing
from qgis.core import QgsProcessingAlgorithm
from qgis.core import QgsProcessingMultiStepFeedback
from qgis.core import QgsProcessingParameterVectorLayer
from qgis.core import QgsProcessingParameterFeatureSink
import processing


class Mymodel2(QgsProcessingAlgorithm):

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterVectorLayer('Carrefour', 'Carrefour branches', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('Carrefourpoints', 'Carrefour points', types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('Quartiers', "POIs (points d'intérêt)", types=[QgsProcessing.TypeVectorPoint], defaultValue=None))
        self.addParameter(QgsProcessingParameterVectorLayer('voies', 'Network (réseau routière de la ville)', types=[QgsProcessing.TypeVectorLine], defaultValue=None))
        self.addParameter(QgsProcessingParameterFeatureSink('Final_layer', 'Carrefour branches nommées', type=QgsProcessing.TypeVectorLine, createByDefault=True, defaultValue=None))
    
    
    def processAlgorithm(self, parameters, context, model_feedback):
        # Use a multi-step feedback, so that individual child algorithm progress reports are adjusted for the
        # overall progress through the model
        feedback = QgsProcessingMultiStepFeedback(15, model_feedback)
        results = {}
        outputs = {}

        # Extract by expression (branches)
        alg_params = {
            'EXPRESSION': "branch != ''",
            'INPUT': parameters['Carrefour'],
            'FAIL_OUTPUT': QgsProcessing.TEMPORARY_OUTPUT,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByExpressionBranches'] = processing.run('native:extractbyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        
        feedback.setCurrentStep(1)
        if feedback.isCanceled():
            return {}

        # Line_angle
        alg_params = {
            'FIELD_LENGTH': 0,
            'FIELD_NAME': 'Line_angle',
            'FIELD_PRECISION': 0,
            'FIELD_TYPE': 0,  # Decimal (double)
            'FORMULA': 'degrees(azimuth(start_point($geometry), end_point($geometry)))',
            'INPUT': outputs['ExtractByExpressionBranches']['OUTPUT'],
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['Line_angle'] = processing.run('native:fieldcalculator', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Branches'] = outputs['Line_angle']['OUTPUT']

        feedback.setCurrentStep(2)
        if feedback.isCanceled():
            return {}
        
        # Join attributes by location
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'INPUT': parameters['Carrefourpoints'],
            'JOIN': outputs['ExtractByExpressionBranches']['FAIL_OUTPUT'],
            'JOIN_FIELDS': ['osmid'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREDICATE': [0],  # intersects
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinAttributesByLocation'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)    

        '''# Join attributes by field value (joined interior points)
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'FIELD': 'osmid',
            'FIELDS_TO_COPY': [''],
            'FIELD_2': 'v',
            'INPUT': parameters['Carrefourpoints'],
            'INPUT_2': outputs['ExtractByExpressionBranches']['FAIL_OUTPUT'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinAttributesByFieldValueJoinedInteriorPoints'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)'''

        feedback.setCurrentStep(3)
        if feedback.isCanceled():
            return {}

        # Extract specific vertices (arrivée)
        alg_params = {
            'INPUT': outputs['Line_angle']['OUTPUT'],
            'VERTICES': '-1',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractSpecificVerticesArrive'] = processing.run('native:extractspecificvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(4)
        if feedback.isCanceled():
            return {}

        # Extract specific vertices (départ)
        alg_params = {
            'INPUT': outputs['Line_angle']['OUTPUT'],
            'VERTICES': '0',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractSpecificVerticesDpart'] = processing.run('native:extractspecificvertices', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(5)
        if feedback.isCanceled():
            return {}

        # Join attributes by location ( arrivée)
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'INPUT': outputs['ExtractSpecificVerticesArrive']['OUTPUT'],
            'JOIN': outputs['JoinAttributesByLocation']['OUTPUT'],
            'JOIN_FIELDS': ['osmid'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREDICATE': [2],  # equal
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinAttributesByLocationArrive'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(6)
        if feedback.isCanceled():
            return {}

        # Join attributes by location (départ)
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'INPUT': outputs['ExtractSpecificVerticesDpart']['OUTPUT'],
            'JOIN': outputs['JoinAttributesByLocation']['OUTPUT'],
            'JOIN_FIELDS': ['osmid'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREDICATE': [2],  # equal
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinAttributesByLocationDpart'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(7)
        if feedback.isCanceled():
            return {}

        # Geometry by expression(départ)
        alg_params = {
            'EXPRESSION': 'wedge_buffer($geometry, Line_angle, 35, 0.04)',
            'INPUT': outputs['JoinAttributesByLocationDpart']['OUTPUT'],
            'OUTPUT_GEOMETRY': 0,  # Polygon
            'WITH_M': False,
            'WITH_Z': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GeometryByExpressiondpart'] = processing.run('native:geometrybyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['WedgeBufferDpart'] = outputs['GeometryByExpressiondpart']['OUTPUT']

        feedback.setCurrentStep(8)
        if feedback.isCanceled():
            return {}

        # Geometry by expression(arrivée)
        alg_params = {
            'EXPRESSION': 'wedge_buffer($geometry, Line_angle+180, 35, 0.04)',
            'INPUT': outputs['JoinAttributesByLocationArrive']['OUTPUT'],
            'OUTPUT_GEOMETRY': 0,  # Polygon
            'WITH_M': False,
            'WITH_Z': False,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['GeometryByExpressionarrive'] = processing.run('native:geometrybyexpression', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['WedgeBufferArrive'] = outputs['GeometryByExpressionarrive']['OUTPUT']

        feedback.setCurrentStep(9)
        if feedback.isCanceled():
            return {}

        # Merge vector layers (points_branches)
        alg_params = {
            'CRS': 'ProjectCrs',
            'LAYERS': [outputs['JoinAttributesByLocationDpart']['OUTPUT'],outputs['JoinAttributesByLocationArrive']['OUTPUT']],
            'OUTPUT': processing.getTempFilename("merged79")
        }
        outputs['MergeVectorLayersPoints_branches'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Points_branches'] = outputs['MergeVectorLayersPoints_branches']['OUTPUT']
        

        feedback.setCurrentStep(10)
        if feedback.isCanceled():
            return {}

        # Extract by location (arrivée)
        alg_params = {
            'INPUT': parameters['Quartiers'],
            'INTERSECT': outputs['GeometryByExpressionarrive']['OUTPUT'],
            #'OUTPUT': 'C:/Users/jayat/AppData/Roaming/QGIS/QGIS3/profiles/default/processing/outputs/Ali/nom.shp',
            'PREDICATE': [0],  # intersect
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByLocationArrive'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(11)
        if feedback.isCanceled():
            return {}

        # Extract by location (départ)
        alg_params = {
            'INPUT': parameters['Quartiers'],
            'INTERSECT': outputs['GeometryByExpressiondpart']['OUTPUT'],
            'PREDICATE': [0],  # intersect
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['ExtractByLocationDpart'] = processing.run('native:extractbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(12)
        if feedback.isCanceled():
            return {}

        # Join osmid by location (arrivée)
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'INPUT': outputs['ExtractByLocationArrive']['OUTPUT'],
            'JOIN': outputs['GeometryByExpressionarrive']['OUTPUT'],
            'JOIN_FIELDS': ['osmid'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREDICATE': [0],  # intersect
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinOsmidByLocationArrive'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(13)
        if feedback.isCanceled():
            return {}

        # Join osmid by location (départ)
        alg_params = {
            'DISCARD_NONMATCHING': True,
            'INPUT': outputs['ExtractByLocationDpart']['OUTPUT'],
            'JOIN': outputs['GeometryByExpressiondpart']['OUTPUT'],
            'JOIN_FIELDS': ['osmid'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREDICATE': [0],  # intersect
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinOsmidByLocationDpart'] = processing.run('native:joinattributesbylocation', alg_params, context=context, feedback=feedback, is_child_algorithm=True)

        feedback.setCurrentStep(14)
        if feedback.isCanceled():
            return {}

        # Merge vector layers (valid quartiers)
        alg_params = {
            'CRS': 'ProjectCrs',
            'LAYERS': [outputs['JoinOsmidByLocationArrive']['OUTPUT'],outputs['JoinOsmidByLocationDpart']['OUTPUT']],
            'OUTPUT': processing.getTempFilename("merged80")
        }
        outputs['MergeVectorLayersValidQuartiers'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Valid_quartiers'] = outputs['MergeVectorLayersValidQuartiers']['OUTPUT']
        
        
        
        feedback.setCurrentStep(15)
        if feedback.isCanceled():
            return {}
            
        # Shortest path (point to layer)
        start_points = QgsVectorLayer(results['Points_branches'], 'nom', 'ogr')
        end_points = QgsVectorLayer(results['Valid_quartiers'], 'nom', 'ogr')
        compteur = 0
        
        for feat in start_points.getFeatures():
            #for feat2 in end_points.getFeatures():
            end_points.removeSelection()
            compteur = compteur+1
            fn = '{}{}{}'.format("C:\\Users\\jayat\\Documents\\AouiniAli\\output\\expo",compteur,".shp")

            for feat2 in end_points.getFeatures():
                #fn = '{}{}{}'.format("C:\\Users\\jayat\\Documents\\AouiniAli\\output\\expo",compteur,".shp")
                start_point_id = feat["osmid"]
                end_point_id = feat2["osmid"]
                start_point_geom = feat.geometry()
                end_point_geom = feat2.geometry()
                if start_point_id == end_point_id:
        
                    end_points.select(feat2.id())
    
            writer = QgsVectorFileWriter.writeAsVectorFormat(end_points, fn, 'utf-8', driverName='ESRI Shapefile', onlySelected=True)
            #start_point_id = feat["osmid"]
            #end_point_id = feat2["osmid"]
            #start_point_geom = feat.geometry()
            #end_point_geom = feat2.geometry()
            #if start_point_id == end_point_id:
        liste = []
        Compteur = 0 
        for feat in start_points.getFeatures():
            start_point_geom = feat.geometry()
            Compteur = Compteur + 1
            
            Fn = '{}{}{}'.format("C:\\Users\\jayat\\Documents\\AouiniAli\\output\\expo",Compteur,".shp")
                
            # Shortest path (point to point)
            outputs['ShortestPathPointToLayer'] = processing.run('native:shortestpathpointtolayer', {
            #alg_params = {
            'DEFAULT_DIRECTION': 2,  # Both directions
            'DEFAULT_SPEED': 50,
            'DIRECTION_FIELD': '',
            'END_POINTS': Fn,
            'INPUT': parameters['voies'],
            'SPEED_FIELD': '',
            'START_POINT': start_point_geom,
            'STRATEGY': 0,  # Shortest
            'TOLERANCE': 0,
            'VALUE_BACKWARD': '',
            'VALUE_BOTH': '',
            'VALUE_FORWARD': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
            }, context=context, feedback=feedback, is_child_algorithm=True)
                    
            #outputs['ShortestPathPointToLayer'] = processing.run('native:shortestpathpointtopoint', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            results['Meilleurs_chemins'] = outputs['ShortestPathPointToLayer']['OUTPUT']
            liste.append(results['Meilleurs_chemins'])
        
        feedback.setCurrentStep(16)
        if feedback.isCanceled():
            return {}
        
        # Select by expression
        liste_extracted = []
        for i in liste:
            #print(i)
            
            processing.run('qgis:selectbyexpression',{
            #alg_params = {
                'EXPRESSION': '"cost" = minimum("cost")',
                'INPUT': i,
                'METHOD': 0,  # creating new selection
                },context=context, feedback=feedback, is_child_algorithm=True)
            
            # Extract selected features (shortest path extracted)
            alg_params = {
                'INPUT': i,
                'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
                }
        
            outputs['ExtractSelectedFeatures'] = processing.run('native:saveselectedfeatures', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
            results['Extracted_shortest_path'] = outputs['ExtractSelectedFeatures']['OUTPUT']
            liste_extracted.append(results['Extracted_shortest_path'])
            
        
        feedback.setCurrentStep(17)
        if feedback.isCanceled():
            return {}
        
        # Merge vector layers (extracted shortest paths)
        alg_params = {
            'CRS': 'ProjectCrs',
            'LAYERS': liste_extracted,
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['MergeVectorLayersExtracted'] = processing.run('native:mergevectorlayers', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Merged_extracted'] = outputs['MergeVectorLayersExtracted']['OUTPUT']
        
        feedback.setCurrentStep(18)
        if feedback.isCanceled():
            return {}
        
        
        # Join attributes by field value (carrefour branches osmid)
        alg_params = {
            'DISCARD_NONMATCHING': False,
            'FIELD': 'u',
            'FIELDS_TO_COPY': ['osmid'],
            'FIELD_2': 'u',
            'INPUT': parameters['Carrefour'],
            'INPUT_2': results['Points_branches'],
            'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
            'PREFIX': '',
            'OUTPUT': QgsProcessing.TEMPORARY_OUTPUT
        }
        outputs['JoinAttributesByFieldValue'] = processing.run('native:joinattributestable', alg_params, context=context, feedback=feedback, is_child_algorithm=True)
        results['Carrefour_branches_joined'] = outputs['JoinAttributesByFieldValue']['OUTPUT']
        
        feedback.setCurrentStep(19)
        if feedback.isCanceled():
            return {}
        
        # Join attributes by field value (carrefour branches branche_name)
        
        #liste_output = []
        #for i in liste_extracted:
        outputs['Carrefour_branches_extracted'] = processing.run('native:joinattributestable',{
            
        #alg_params = {
        'DISCARD_NONMATCHING': False,
        'FIELD': 'osmid',
        'FIELDS_TO_COPY': ['name'],
        'FIELD_2': 'osmid',
        'INPUT': results['Carrefour_branches_joined'],
        'INPUT_2': results['Merged_extracted'],
        'METHOD': 1,  # Take attributes of the first matching feature only (one-to-one)
        'PREFIX': '',
        'OUTPUT': parameters['Final_layer']
        }, context=context, feedback=feedback, is_child_algorithm=True)
       
        print(outputs['Carrefour_branches_extracted'])
        print(type(outputs['Carrefour_branches_extracted']))
        #liste_output.append(parameters['Final_layer'])
        
        results['Final_layer'] = outputs['Carrefour_branches_extracted']['OUTPUT']
        
        return results

    def name(self):
        return 'mymodel2'

    def displayName(self):
        return 'mymodel2'

    def group(self):
        return ''

    def groupId(self):
        return ''

    def createInstance(self):
        return Mymodel2()
