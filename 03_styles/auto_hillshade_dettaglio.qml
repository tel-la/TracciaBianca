<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.44.14-Solothurn" styleCategories="Symbology|Labeling">
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option type="QString" value="" name="name"/>
      <Option name="properties"/>
      <Option type="QString" value="collection" name="type"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling zoomedOutResamplingMethod="nearestNeighbour" enabled="false" zoomedInResamplingMethod="nearestNeighbour" maxOversampling="2"/>
    </provider>
    <rasterrenderer grayBand="1" type="singlebandgray" alphaBand="-1" gradient="BlackToWhite" opacity="0.3" nodataColor="">
      <minMaxOrigin>
        <limits>None</limits>
        <extent>WholeRaster</extent>
        <statAccuracy>Estimated</statAccuracy>
        <cumulativeCutLower>0.02</cumulativeCutLower>
        <cumulativeCutUpper>0.98</cumulativeCutUpper>
        <stdDevFactor>2</stdDevFactor>
      </minMaxOrigin>
      <contrastEnhancement>
        <minValue>0</minValue>
        <maxValue>255</maxValue>
        <algorithm>StretchToMinimumMaximum</algorithm>
      </contrastEnhancement>
      <rampLegendSettings prefix="" useContinuousLegend="1" minimumLabel="" direction="0" orientation="2" maximumLabel="" suffix="">
        <numericFormat id="basic">
          <Option type="Map">
            <Option type="invalid" name="decimal_separator"/>
            <Option type="int" value="6" name="decimals"/>
            <Option type="int" value="0" name="rounding_type"/>
            <Option type="bool" value="false" name="show_plus"/>
            <Option type="bool" value="true" name="show_thousand_separator"/>
            <Option type="bool" value="false" name="show_trailing_zeros"/>
            <Option type="invalid" name="thousand_separator"/>
          </Option>
        </numericFormat>
      </rampLegendSettings>
    </rasterrenderer>
    <brightnesscontrast brightness="0" gamma="1" contrast="0"/>
    <huesaturation colorizeBlue="128" colorizeStrength="100" colorizeOn="0" invertColors="0" saturation="0" grayscaleMode="0" colorizeRed="255" colorizeGreen="128"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
