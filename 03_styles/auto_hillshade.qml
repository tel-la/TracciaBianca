<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.44.14-Solothurn" styleCategories="Symbology|Labeling">
  <pipe-data-defined-properties>
    <Option type="Map">
      <Option type="QString" name="name" value=""/>
      <Option name="properties"/>
      <Option type="QString" name="type" value="collection"/>
    </Option>
  </pipe-data-defined-properties>
  <pipe>
    <provider>
      <resampling enabled="false" zoomedInResamplingMethod="nearestNeighbour" zoomedOutResamplingMethod="nearestNeighbour" maxOversampling="2"/>
    </provider>
    <rasterrenderer type="singlebandgray" nodataColor="" grayBand="1" opacity="0.43" gradient="BlackToWhite" alphaBand="-1">
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
      <rampLegendSettings direction="0" orientation="2" minimumLabel="" useContinuousLegend="1" suffix="" maximumLabel="" prefix="">
        <numericFormat id="basic">
          <Option type="Map">
            <Option type="invalid" name="decimal_separator"/>
            <Option type="int" name="decimals" value="6"/>
            <Option type="int" name="rounding_type" value="0"/>
            <Option type="bool" name="show_plus" value="false"/>
            <Option type="bool" name="show_thousand_separator" value="true"/>
            <Option type="bool" name="show_trailing_zeros" value="false"/>
            <Option type="invalid" name="thousand_separator"/>
          </Option>
        </numericFormat>
      </rampLegendSettings>
    </rasterrenderer>
    <brightnesscontrast contrast="0" gamma="1" brightness="0"/>
    <huesaturation grayscaleMode="0" colorizeBlue="128" colorizeRed="255" colorizeGreen="128" invertColors="0" colorizeOn="0" colorizeStrength="100" saturation="0"/>
    <rasterresampler maxOversampling="2"/>
    <resamplingStage>resamplingFilter</resamplingStage>
  </pipe>
  <blendMode>0</blendMode>
</qgis>
