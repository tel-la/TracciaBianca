"""Anteprime locali alla stessa griglia Mercator/96 DPI del MBTiles."""
import argparse
import json
from pathlib import Path

from qgis.core import (QgsApplication, QgsProject, QgsMapSettings, QgsRectangle,
                       QgsMapRendererSequentialJob, QgsCoordinateReferenceSystem, QgsVectorLayer, QgsExpressionContext, QgsExpressionContextUtils)
from qgis.PyQt.QtCore import QSize
from qgis.PyQt.QtGui import QColor

from scialpinismo.engine import load_json, geometry_in, save_json

_app = None

def main():
    global _app
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('area',type=Path)
    parser.add_argument('--no-labels',action='store_true',help='Diagnostica del solo disegno geometrico')
    parser.add_argument('--only',choices=['centro_abitato','rifugio','bivacco','lago','ghiacciaio','bosco','panorama'])
    args=parser.parse_args()
    _app=QgsApplication([],False);_app.initQgis()
    area=args.area.resolve();config=load_json(area/'area.json');project=QgsProject()
    if not project.read(str(area/config['project'])):raise RuntimeError('Progetto non leggibile')
    output=area/'output/anteprime';output.mkdir(exist_ok=True,parents=True)
    layers=[n.layer() for n in project.layerTreeRoot().findLayers() if n.isVisible()]
    records=[]
    def render(name,extent,size=1000):
        if args.no_labels:name+='_senza_testi'
        settings=QgsMapSettings();settings.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
        settings.setTransformContext(project.transformContext());settings.setLayers(layers)
        settings.setOutputSize(QSize(size,size));settings.setOutputDpi(96)
        settings.setBackgroundColor(QColor('#fffdf5'));settings.setExtent(extent)
        context=QgsExpressionContext();context.appendScope(QgsExpressionContextUtils.globalScope());context.appendScope(QgsExpressionContextUtils.projectScope(project));context.appendScope(QgsExpressionContextUtils.mapSettingsScope(settings));settings.setExpressionContext(context)
        if args.no_labels:
            from qgis.core import Qgis
            settings.setFlag(Qgis.MapSettingsFlag.DrawLabeling,False)
        print('Rendering',name,'scale',round(settings.scale()),flush=True)
        job=QgsMapRendererSequentialJob(settings);job.start();job.waitForFinished()
        path=output/(name+'.png')
        if not job.renderedImage().save(str(path)):raise RuntimeError('Anteprima non salvata')
        labeling=job.takeLabelingResults()
        hut_ids={layer.id() for layer in layers if layer.source().endswith('|layername=rifugi')}
        hut_labels=sorted({pos.labelText for pos in labeling.labelsWithinRect(settings.extent()) if pos.layerID in hut_ids}) if labeling else []
        contour_ids={layer.id() for layer in layers if '|layername=curve_' in layer.source()}
        contour_labels=[pos.labelText for pos in labeling.labelsWithinRect(settings.extent()) if pos.layerID in contour_ids] if labeling else []
        records.append({'file':path.name,'scale':settings.scale(),'dpi':96,'mountain_hut_labels':hut_labels,'contour_labels':contour_labels})
    from qgis.core import QgsGeometry
    geom=geometry_in(QgsGeometry.fromWkt(config['perimeter_wkt']),config['perimeter_crs'],'EPSG:3857')
    for table,keyword,stem in [('poi',None,'centro_abitato'),('rifugi','giussani','rifugio'),('rifugi','bivacco della pace','bivacco'),
                               ('acque','misurina','lago'),('acque','ghiacciaio','ghiacciaio')]:
        if args.only and args.only!=stem:continue
        layer=QgsVectorLayer(str(area/'vettori/dati_area.gpkg')+'|layername='+table,table,'ogr')
        features=([f for f in layer.getFeatures() if f['place'] in ('town','village','hamlet') and f['label']]
                  if stem == 'centro_abitato' else
                  [f for f in layer.getFeatures() if keyword in str(f['label']).casefold()])
        if not features and stem=='ghiacciaio':
            features=[f for f in layer.getFeatures() if f['categoria']=='ghiacciaio']
        if not features:continue
        feature=features[0]
        center=geometry_in(feature.geometry().centroid(),layer.crs().authid(),'EPSG:3857').asPoint()
        zooms = ((12,13,14,15) if stem == 'centro_abitato' else
                 (12,14,15,16,17) if stem == 'rifugio' else (16,17))
        for zoom in zooms:
            width=1024
            span=40075016.68557849/(2**zoom)*(width/256)
            render(f'{stem}_z{zoom}_corrente',QgsRectangle(center.x()-span/2,center.y()-span/2,center.x()+span/2,center.y()+span/2),width)
    if not args.only or args.only=='bosco':
        layer=QgsVectorLayer(str(area/'vettori/dati_area.gpkg')+'|layername=vegetazione','boschi','ogr')
        candidates=[f for f in layer.getFeatures() if f['leaf_type']=='needleleaved' and (f['natural']=='wood' or f['landuse']=='forest')]
        if candidates:
            feature=max(candidates,key=lambda f:f.geometry().area())
            center=geometry_in(feature.geometry().pointOnSurface(),layer.crs().authid(),'EPSG:3857').asPoint()
            span=40075016.68557849/(2**16)*4
            render('bosco_z16_corrente',QgsRectangle(center.x()-span/2,center.y()-span/2,center.x()+span/2,center.y()+span/2),1024)
    if not args.only or args.only=='panorama':render('panorama_corrente',geom.boundingBox(),1200)
    save_json(output/'anteprime_correnti.json',records)
    print(json.dumps(records,indent=2))


if __name__=='__main__':
    main()
    _app.exitQgis()
