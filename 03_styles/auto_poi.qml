<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis labelsEnabled="1" styleCategories="Symbology|Labeling" version="3.44.14-Solothurn">
  <renderer-v2 referencescale="-1" forceraster="0" type="RuleRenderer" enableorderby="0" symbollevels="0">
    <rules key="{cfc67c40-e5ef-44bd-b3de-12a76deaf2a1}">
      <rule key="{43bed691-8bb6-4620-93cf-cfd163ed0e4b}" label="Vette" filter="(TRUE) AND &quot;natural&quot; = 'peak'" symbol="0"/>
      <rule key="{470ca8f2-9b76-4393-8637-d095847c10e6}" label="Colli" filter="(TRUE) AND &quot;natural&quot; = 'saddle'" symbol="1"/>
      <rule key="{03a0d06e-6dc5-4ed9-adc1-65e9de26a200}" label="Parcheggi — zoom 15" filter="&quot;amenity&quot; = 'parking' AND @map_scale >= @scialpinismo_scale_15_16" symbol="2"/>
      <rule key="{876496a5-dd50-42a4-9b0e-cbff5f8825f2}" label="Parcheggi compatti — zoom 16+" filter="&quot;amenity&quot; = 'parking' AND @map_scale &lt; @scialpinismo_scale_15_16" symbol="3"/>
      <rule key="{4171e815-cabd-4936-b2f4-cb97e9cbb33a}" label="Centri abitati e riferimenti" filter="(TRUE) AND NOT (&quot;natural&quot; IN ('peak','saddle')) AND NOT (&quot;amenity&quot; = 'parking')" symbol="4"/>
    </rules>
    <symbols>
      <symbol alpha="1" type="marker" is_animated="0" name="0" clip_to_extent="1" frame_rate="10" force_rhr="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" value="" name="name"/>
            <Option name="properties"/>
            <Option type="QString" value="collection" name="type"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" locked="0" pass="0" enabled="1" id="{e0a706f3-5761-452c-bdd6-5be143145ae0}">
          <Option type="Map">
            <Option type="QString" value="0" name="angle"/>
            <Option type="QString" value="square" name="cap_style"/>
            <Option type="QString" value="102,89,77,255,rgb:0.4,0.3490196,0.3019608,1" name="color"/>
            <Option type="QString" value="1" name="horizontal_anchor_point"/>
            <Option type="QString" value="bevel" name="joinstyle"/>
            <Option type="QString" value="triangle" name="name"/>
            <Option type="QString" value="0,0" name="offset"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="offset_map_unit_scale"/>
            <Option type="QString" value="MM" name="offset_unit"/>
            <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="outline_color"/>
            <Option type="QString" value="solid" name="outline_style"/>
            <Option type="QString" value="0.25" name="outline_width"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="outline_width_map_unit_scale"/>
            <Option type="QString" value="MM" name="outline_width_unit"/>
            <Option type="QString" value="diameter" name="scale_method"/>
            <Option type="QString" value="2" name="size"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="size_map_unit_scale"/>
            <Option type="QString" value="MM" name="size_unit"/>
            <Option type="QString" value="1" name="vertical_anchor_point"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option name="properties"/>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" is_animated="0" name="1" clip_to_extent="1" frame_rate="10" force_rhr="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" value="" name="name"/>
            <Option name="properties"/>
            <Option type="QString" value="collection" name="type"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" locked="0" pass="0" enabled="1" id="{685e60e0-38e7-4db1-8e54-59343b22f775}">
          <Option type="Map">
            <Option type="QString" value="0" name="angle"/>
            <Option type="QString" value="square" name="cap_style"/>
            <Option type="QString" value="102,89,77,255,rgb:0.4,0.3490196,0.3019608,1" name="color"/>
            <Option type="QString" value="1" name="horizontal_anchor_point"/>
            <Option type="QString" value="bevel" name="joinstyle"/>
            <Option type="QString" value="triangle" name="name"/>
            <Option type="QString" value="0,0" name="offset"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="offset_map_unit_scale"/>
            <Option type="QString" value="MM" name="offset_unit"/>
            <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="outline_color"/>
            <Option type="QString" value="solid" name="outline_style"/>
            <Option type="QString" value="0.2" name="outline_width"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="outline_width_map_unit_scale"/>
            <Option type="QString" value="MM" name="outline_width_unit"/>
            <Option type="QString" value="diameter" name="scale_method"/>
            <Option type="QString" value="1.6" name="size"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="size_map_unit_scale"/>
            <Option type="QString" value="MM" name="size_unit"/>
            <Option type="QString" value="1" name="vertical_anchor_point"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option name="properties"/>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" is_animated="0" name="2" clip_to_extent="1" frame_rate="10" force_rhr="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" value="" name="name"/>
            <Option name="properties"/>
            <Option type="QString" value="collection" name="type"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" locked="0" pass="0" enabled="1" id="{2a7888c2-10c8-47ee-8e73-c4495342392d}">
          <Option type="Map">
            <Option type="QString" value="0" name="angle"/>
            <Option type="QString" value="square" name="cap_style"/>
            <Option type="QString" value="23,105,170,255,rgb:0.0901961,0.4117647,0.6666667,1" name="color"/>
            <Option type="QString" value="1" name="horizontal_anchor_point"/>
            <Option type="QString" value="round" name="joinstyle"/>
            <Option type="QString" value="square" name="name"/>
            <Option type="QString" value="0,0" name="offset"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="offset_map_unit_scale"/>
            <Option type="QString" value="MM" name="offset_unit"/>
            <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="outline_color"/>
            <Option type="QString" value="solid" name="outline_style"/>
            <Option type="QString" value="0.34" name="outline_width"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="outline_width_map_unit_scale"/>
            <Option type="QString" value="MM" name="outline_width_unit"/>
            <Option type="QString" value="diameter" name="scale_method"/>
            <Option type="QString" value="3.05" name="size"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="size_map_unit_scale"/>
            <Option type="QString" value="MM" name="size_unit"/>
            <Option type="QString" value="1" name="vertical_anchor_point"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option name="properties"/>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
        <layer class="FontMarker" locked="0" pass="0" enabled="1" id="{c0d56395-e48d-4f60-9a3c-26e3c43a9e0b}">
          <Option type="Map">
            <Option type="QString" value="0" name="angle"/>
            <Option type="QString" value="P" name="chr"/>
            <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="color"/>
            <Option type="QString" value="Arial" name="font"/>
            <Option type="QString" value="Bold" name="font_style"/>
            <Option type="QString" value="1" name="horizontal_anchor_point"/>
            <Option type="QString" value="miter" name="joinstyle"/>
            <Option type="QString" value="0,0" name="offset"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="offset_map_unit_scale"/>
            <Option type="QString" value="MM" name="offset_unit"/>
            <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="outline_color"/>
            <Option type="QString" value="0" name="outline_width"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="outline_width_map_unit_scale"/>
            <Option type="QString" value="MM" name="outline_width_unit"/>
            <Option type="QString" value="2.05" name="size"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="size_map_unit_scale"/>
            <Option type="QString" value="MM" name="size_unit"/>
            <Option type="QString" value="1" name="vertical_anchor_point"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option name="properties"/>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" is_animated="0" name="3" clip_to_extent="1" frame_rate="10" force_rhr="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" value="" name="name"/>
            <Option name="properties"/>
            <Option type="QString" value="collection" name="type"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" locked="0" pass="0" enabled="1" id="{5da08fc6-bd55-41ba-ba2f-07fe96502442}">
          <Option type="Map">
            <Option type="QString" value="0" name="angle"/>
            <Option type="QString" value="square" name="cap_style"/>
            <Option type="QString" value="23,105,170,255,rgb:0.0901961,0.4117647,0.6666667,1" name="color"/>
            <Option type="QString" value="1" name="horizontal_anchor_point"/>
            <Option type="QString" value="round" name="joinstyle"/>
            <Option type="QString" value="square" name="name"/>
            <Option type="QString" value="0,0" name="offset"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="offset_map_unit_scale"/>
            <Option type="QString" value="MM" name="offset_unit"/>
            <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="outline_color"/>
            <Option type="QString" value="solid" name="outline_style"/>
            <Option type="QString" value="0.28" name="outline_width"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="outline_width_map_unit_scale"/>
            <Option type="QString" value="MM" name="outline_width_unit"/>
            <Option type="QString" value="diameter" name="scale_method"/>
            <Option type="QString" value="2.15" name="size"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="size_map_unit_scale"/>
            <Option type="QString" value="MM" name="size_unit"/>
            <Option type="QString" value="1" name="vertical_anchor_point"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option name="properties"/>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
        <layer class="FontMarker" locked="0" pass="0" enabled="1" id="{75afe981-73cc-42ad-936c-32fa3b83099e}">
          <Option type="Map">
            <Option type="QString" value="0" name="angle"/>
            <Option type="QString" value="P" name="chr"/>
            <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="color"/>
            <Option type="QString" value="Arial" name="font"/>
            <Option type="QString" value="Bold" name="font_style"/>
            <Option type="QString" value="1" name="horizontal_anchor_point"/>
            <Option type="QString" value="miter" name="joinstyle"/>
            <Option type="QString" value="0,0" name="offset"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="offset_map_unit_scale"/>
            <Option type="QString" value="MM" name="offset_unit"/>
            <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="outline_color"/>
            <Option type="QString" value="0" name="outline_width"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="outline_width_map_unit_scale"/>
            <Option type="QString" value="MM" name="outline_width_unit"/>
            <Option type="QString" value="1.42" name="size"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="size_map_unit_scale"/>
            <Option type="QString" value="MM" name="size_unit"/>
            <Option type="QString" value="1" name="vertical_anchor_point"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option name="properties"/>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
      <symbol alpha="1" type="marker" is_animated="0" name="4" clip_to_extent="1" frame_rate="10" force_rhr="0">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" value="" name="name"/>
            <Option name="properties"/>
            <Option type="QString" value="collection" name="type"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" locked="0" pass="0" enabled="1" id="{b3ed04fe-a800-4264-b30b-629119d94e1f}">
          <Option type="Map">
            <Option type="QString" value="0" name="angle"/>
            <Option type="QString" value="square" name="cap_style"/>
            <Option type="QString" value="96,91,85,255,rgb:0.3764706,0.3568627,0.3333333,1" name="color"/>
            <Option type="QString" value="1" name="horizontal_anchor_point"/>
            <Option type="QString" value="bevel" name="joinstyle"/>
            <Option type="QString" value="circle" name="name"/>
            <Option type="QString" value="0,0" name="offset"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="offset_map_unit_scale"/>
            <Option type="QString" value="MM" name="offset_unit"/>
            <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="outline_color"/>
            <Option type="QString" value="solid" name="outline_style"/>
            <Option type="QString" value="0.15" name="outline_width"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="outline_width_map_unit_scale"/>
            <Option type="QString" value="MM" name="outline_width_unit"/>
            <Option type="QString" value="diameter" name="scale_method"/>
            <Option type="QString" value="0.7" name="size"/>
            <Option type="QString" value="3x:0,0,0,0,0,0" name="size_map_unit_scale"/>
            <Option type="QString" value="MM" name="size_unit"/>
            <Option type="QString" value="1" name="vertical_anchor_point"/>
          </Option>
          <data_defined_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option name="properties"/>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </data_defined_properties>
        </layer>
      </symbol>
    </symbols>
    <data-defined-properties>
      <Option type="Map">
        <Option type="QString" value="" name="name"/>
        <Option name="properties"/>
        <Option type="QString" value="collection" name="type"/>
      </Option>
    </data-defined-properties>
  </renderer-v2>
  <selection mode="Default">
    <selectionColor invalid="1"/>
  </selection>
  <labeling type="rule-based">
    <rules key="{538396d5-bb3a-40d7-b7cb-a94514d1e54d}">
      <rule key="{c563c42b-6ded-4b52-a986-57bf99dd9c4a}" filter="(TRUE) AND (&quot;place&quot; IN ('town','village','hamlet')) AND NOT (&quot;amenity&quot; = 'parking')">
        <settings calloutType="simple">
          <text-style namedStyle="" forcedItalic="0" tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0" fontWeight="75" capitalization="0" forcedBold="0" blendMode="0" fontWordSpacing="0" legendString="Aa" fontLetterSpacing="0" tabStopDistanceUnit="Percentage" allowHtml="0" tabStopDistance="6" fieldName="CASE WHEN &quot;natural&quot; = 'peak' AND @map_scale &lt; @scialpinismo_scale_15_16 AND nullif(trim(&quot;ele&quot;),'') IS NOT NULL THEN concat(coalesce(nullif(&quot;label&quot;,''),''), CASE WHEN nullif(&quot;label&quot;,'') IS NOT NULL THEN ' · ' ELSE '' END, regexp_replace(trim(&quot;ele&quot;), '\\s*m\\s*$', ''), ' m') ELSE &quot;label&quot; END" fontKerning="1" fontSizeMapUnitScale="3x:0,0,0,0,0,0" multilineHeight="1" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" fontSizeUnit="Point" fontStrikeout="0" useSubstitutions="0" textColor="37,37,37,255,rgb:0.145098,0.145098,0.145098,1" fontItalic="0" isExpression="1" textOrientation="horizontal" fontFamily="Arial" fontUnderline="0" multilineHeightUnit="Percentage" fontSize="12.5" textOpacity="1">
            <families/>
            <text-buffer bufferBlendMode="0" bufferColor="255,254,250,255,rgb:1,0.9960784,0.9803922,1" bufferSize="0.71999999999999997" bufferDraw="1" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferSizeUnits="MM" bufferNoFill="1" bufferJoinStyle="128" bufferOpacity="1"/>
            <text-mask maskSize2="1.5" maskSizeUnits="MM" maskedSymbolLayers="" maskJoinStyle="128" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskOpacity="1" maskType="0" maskEnabled="0" maskSize="1.5"/>
            <background shapeRotation="0" shapeOpacity="1" shapeOffsetUnit="MM" shapeBorderColor="128,128,128,255,rgb:0.5019608,0.5019608,0.5019608,1" shapeBorderWidthUnit="MM" shapeSVGFile="" shapeRotationType="0" shapeJoinStyle="64" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeDraw="0" shapeSizeUnit="MM" shapeSizeType="0" shapeRadiiUnit="MM" shapeOffsetX="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetY="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeBlendMode="0" shapeRadiiX="0" shapeRadiiY="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeFillColor="255,255,255,255,rgb:1,1,1,1" shapeBorderWidth="0" shapeSizeX="0" shapeType="0" shapeSizeY="0">
              <symbol alpha="1" type="fill" is_animated="0" name="fillSymbol" clip_to_extent="1" frame_rate="10" force_rhr="0">
                <data_defined_properties>
                  <Option type="Map">
                    <Option type="QString" value="" name="name"/>
                    <Option name="properties"/>
                    <Option type="QString" value="collection" name="type"/>
                  </Option>
                </data_defined_properties>
                <layer class="SimpleFill" locked="0" pass="0" enabled="1" id="">
                  <Option type="Map">
                    <Option type="QString" value="3x:0,0,0,0,0,0" name="border_width_map_unit_scale"/>
                    <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="color"/>
                    <Option type="QString" value="bevel" name="joinstyle"/>
                    <Option type="QString" value="0,0" name="offset"/>
                    <Option type="QString" value="3x:0,0,0,0,0,0" name="offset_map_unit_scale"/>
                    <Option type="QString" value="MM" name="offset_unit"/>
                    <Option type="QString" value="128,128,128,255,rgb:0.5019608,0.5019608,0.5019608,1" name="outline_color"/>
                    <Option type="QString" value="no" name="outline_style"/>
                    <Option type="QString" value="0" name="outline_width"/>
                    <Option type="QString" value="MM" name="outline_width_unit"/>
                    <Option type="QString" value="solid" name="style"/>
                  </Option>
                  <data_defined_properties>
                    <Option type="Map">
                      <Option type="QString" value="" name="name"/>
                      <Option name="properties"/>
                      <Option type="QString" value="collection" name="type"/>
                    </Option>
                  </data_defined_properties>
                </layer>
              </symbol>
            </background>
            <shadow shadowOffsetUnit="MM" shadowDraw="0" shadowBlendMode="6" shadowRadius="1.5" shadowOpacity="0.69999999999999996" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetAngle="135" shadowOffsetGlobal="1" shadowUnder="0" shadowOffsetDist="1" shadowColor="0,0,0,255,rgb:0,0,0,1" shadowRadiusUnit="MM" shadowRadiusAlphaOnly="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowScale="100"/>
            <dd_properties>
              <Option type="Map">
                <Option type="QString" value="" name="name"/>
                <Option name="properties"/>
                <Option type="QString" value="collection" name="type"/>
              </Option>
            </dd_properties>
            <substitutions/>
          </text-style>
          <text-format useMaxLineLengthForAutoWrap="1" rightDirectionSymbol=">" formatNumbers="0" plussign="0" multilineAlign="3" leftDirectionSymbol="&lt;" addDirectionSymbol="0" reverseDirectionSymbol="0" autoWrapLength="0" decimals="3" wrapChar="" placeDirectionSymbol="0"/>
          <placement maximumDistance="0" geometryGenerator="" overrunDistance="0" offsetType="0" maximumDistanceUnit="MM" allowDegraded="0" polygonPlacementFlags="2" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" lineAnchorClipping="0" fitInPolygonOnly="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" overlapHandling="PreventOverlap" dist="1.3" placement="6" centroidInside="0" overrunDistanceUnit="MM" maxCurvedCharAngleOut="-25" geometryGeneratorEnabled="0" layerType="UnknownGeometry" prioritization="PreferCloser" centroidWhole="0" yOffset="0" offsetUnits="MM" lineAnchorPercent="0.5" quadOffset="4" geometryGeneratorType="PointGeometry" maxCurvedCharAngleIn="25" distUnits="MM" preserveRotation="1" repeatDistance="0" distMapUnitScale="3x:0,0,0,0,0,0" maximumDistanceMapUnitScale="3x:0,0,0,0,0,0" lineAnchorTextPoint="FollowPlacement" priority="9" rotationAngle="0" xOffset="0" placementFlags="10" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" lineAnchorType="0" repeatDistanceUnits="MM" rotationUnit="AngleDegrees"/>
          <rendering minFeatureSize="0" obstacleType="1" fontLimitPixelSize="0" obstacle="1" limitNumLabels="0" fontMaxPixelSize="10000" scaleMax="0" fontMinPixelSize="0" drawLabels="1" zIndex="0" labelPerPart="0" maxNumLabels="2000" upsidedownLabels="0" obstacleFactor="1" scaleMin="0" scaleVisibility="0" mergeLines="0" unplacedVisibility="0"/>
          <dd_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="Size">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="CASE WHEN @map_scale &lt; @scialpinismo_scale_12_13 AND @map_scale >= @scialpinismo_scale_15_16 THEN 15.625 ELSE 12.5 END" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </dd_properties>
          <callout type="simple">
            <Option type="Map">
              <Option type="QString" value="pole_of_inaccessibility" name="anchorPoint"/>
              <Option type="int" value="0" name="blendMode"/>
              <Option type="Map" name="ddProperties">
                <Option type="QString" value="" name="name"/>
                <Option name="properties"/>
                <Option type="QString" value="collection" name="type"/>
              </Option>
              <Option type="bool" value="false" name="drawToAllParts"/>
              <Option type="QString" value="0" name="enabled"/>
              <Option type="QString" value="point_on_exterior" name="labelAnchorPoint"/>
              <Option type="QString" value="&lt;symbol alpha=&quot;1&quot; type=&quot;line&quot; is_animated=&quot;0&quot; name=&quot;symbol&quot; clip_to_extent=&quot;1&quot; frame_rate=&quot;10&quot; force_rhr=&quot;0&quot;>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;collection&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;layer class=&quot;SimpleLine&quot; locked=&quot;0&quot; pass=&quot;0&quot; enabled=&quot;1&quot; id=&quot;{0605b168-9f5f-45d1-87bd-22a2eb4de5c0}&quot;>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;align_dash_pattern&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;square&quot; name=&quot;capstyle&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;5;2&quot; name=&quot;customdash&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;customdash_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;customdash_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;dash_pattern_offset&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;dash_pattern_offset_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;dash_pattern_offset_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;draw_inside_polygon&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;bevel&quot; name=&quot;joinstyle&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;60,60,60,255,rgb:0.2352941,0.2352941,0.2352941,1&quot; name=&quot;line_color&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;solid&quot; name=&quot;line_style&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0.3&quot; name=&quot;line_width&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;line_width_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;offset&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;offset_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;offset_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;ring_filter&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;trim_distance_end&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;trim_distance_end_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;trim_distance_end_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;trim_distance_start&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;trim_distance_start_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;trim_distance_start_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;tweak_dash_pattern_on_corners&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;use_custom_dash&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;width_map_unit_scale&quot;/>&lt;/Option>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;collection&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>" name="lineSymbol"/>
              <Option type="double" value="0" name="minLength"/>
              <Option type="QString" value="3x:0,0,0,0,0,0" name="minLengthMapUnitScale"/>
              <Option type="QString" value="MM" name="minLengthUnit"/>
              <Option type="double" value="0" name="offsetFromAnchor"/>
              <Option type="QString" value="3x:0,0,0,0,0,0" name="offsetFromAnchorMapUnitScale"/>
              <Option type="QString" value="MM" name="offsetFromAnchorUnit"/>
              <Option type="double" value="0" name="offsetFromLabel"/>
              <Option type="QString" value="3x:0,0,0,0,0,0" name="offsetFromLabelMapUnitScale"/>
              <Option type="QString" value="MM" name="offsetFromLabelUnit"/>
            </Option>
          </callout>
        </settings>
      </rule>
      <rule key="{6de21713-31df-4a92-883f-8eb921bcba4e}" filter="(TRUE) AND (NOT (&quot;place&quot; IN ('town','village','hamlet'))) AND NOT (&quot;amenity&quot; = 'parking')">
        <settings calloutType="simple">
          <text-style namedStyle="" forcedItalic="0" tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0" fontWeight="50" capitalization="0" forcedBold="0" blendMode="0" fontWordSpacing="0" legendString="Aa" fontLetterSpacing="0" tabStopDistanceUnit="Percentage" allowHtml="0" tabStopDistance="6" fieldName="CASE WHEN &quot;natural&quot; = 'peak' AND @map_scale &lt; @scialpinismo_scale_15_16 AND nullif(trim(&quot;ele&quot;),'') IS NOT NULL THEN concat(coalesce(nullif(&quot;label&quot;,''),''), CASE WHEN nullif(&quot;label&quot;,'') IS NOT NULL THEN ' · ' ELSE '' END, regexp_replace(trim(&quot;ele&quot;), '\\s*m\\s*$', ''), ' m') ELSE &quot;label&quot; END" fontKerning="1" fontSizeMapUnitScale="3x:0,0,0,0,0,0" multilineHeight="1" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" fontSizeUnit="Point" fontStrikeout="0" useSubstitutions="0" textColor="37,37,37,255,rgb:0.145098,0.145098,0.145098,1" fontItalic="0" isExpression="1" textOrientation="horizontal" fontFamily="Arial" fontUnderline="0" multilineHeightUnit="Percentage" fontSize="11" textOpacity="1">
            <families/>
            <text-buffer bufferBlendMode="0" bufferColor="255,254,250,255,rgb:1,0.9960784,0.9803922,1" bufferSize="0.71999999999999997" bufferDraw="1" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferSizeUnits="MM" bufferNoFill="1" bufferJoinStyle="128" bufferOpacity="1"/>
            <text-mask maskSize2="1.5" maskSizeUnits="MM" maskedSymbolLayers="" maskJoinStyle="128" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskOpacity="1" maskType="0" maskEnabled="0" maskSize="1.5"/>
            <background shapeRotation="0" shapeOpacity="1" shapeOffsetUnit="MM" shapeBorderColor="128,128,128,255,rgb:0.5019608,0.5019608,0.5019608,1" shapeBorderWidthUnit="MM" shapeSVGFile="" shapeRotationType="0" shapeJoinStyle="64" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeDraw="0" shapeSizeUnit="MM" shapeSizeType="0" shapeRadiiUnit="MM" shapeOffsetX="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeOffsetY="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeBlendMode="0" shapeRadiiX="0" shapeRadiiY="0" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeFillColor="255,255,255,255,rgb:1,1,1,1" shapeBorderWidth="0" shapeSizeX="0" shapeType="0" shapeSizeY="0">
              <symbol alpha="1" type="fill" is_animated="0" name="fillSymbol" clip_to_extent="1" frame_rate="10" force_rhr="0">
                <data_defined_properties>
                  <Option type="Map">
                    <Option type="QString" value="" name="name"/>
                    <Option name="properties"/>
                    <Option type="QString" value="collection" name="type"/>
                  </Option>
                </data_defined_properties>
                <layer class="SimpleFill" locked="0" pass="0" enabled="1" id="">
                  <Option type="Map">
                    <Option type="QString" value="3x:0,0,0,0,0,0" name="border_width_map_unit_scale"/>
                    <Option type="QString" value="255,255,255,255,rgb:1,1,1,1" name="color"/>
                    <Option type="QString" value="bevel" name="joinstyle"/>
                    <Option type="QString" value="0,0" name="offset"/>
                    <Option type="QString" value="3x:0,0,0,0,0,0" name="offset_map_unit_scale"/>
                    <Option type="QString" value="MM" name="offset_unit"/>
                    <Option type="QString" value="128,128,128,255,rgb:0.5019608,0.5019608,0.5019608,1" name="outline_color"/>
                    <Option type="QString" value="no" name="outline_style"/>
                    <Option type="QString" value="0" name="outline_width"/>
                    <Option type="QString" value="MM" name="outline_width_unit"/>
                    <Option type="QString" value="solid" name="style"/>
                  </Option>
                  <data_defined_properties>
                    <Option type="Map">
                      <Option type="QString" value="" name="name"/>
                      <Option name="properties"/>
                      <Option type="QString" value="collection" name="type"/>
                    </Option>
                  </data_defined_properties>
                </layer>
              </symbol>
            </background>
            <shadow shadowOffsetUnit="MM" shadowDraw="0" shadowBlendMode="6" shadowRadius="1.5" shadowOpacity="0.69999999999999996" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetAngle="135" shadowOffsetGlobal="1" shadowUnder="0" shadowOffsetDist="1" shadowColor="0,0,0,255,rgb:0,0,0,1" shadowRadiusUnit="MM" shadowRadiusAlphaOnly="0" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowScale="100"/>
            <dd_properties>
              <Option type="Map">
                <Option type="QString" value="" name="name"/>
                <Option name="properties"/>
                <Option type="QString" value="collection" name="type"/>
              </Option>
            </dd_properties>
            <substitutions/>
          </text-style>
          <text-format useMaxLineLengthForAutoWrap="1" rightDirectionSymbol=">" formatNumbers="0" plussign="0" multilineAlign="3" leftDirectionSymbol="&lt;" addDirectionSymbol="0" reverseDirectionSymbol="0" autoWrapLength="0" decimals="3" wrapChar="" placeDirectionSymbol="0"/>
          <placement maximumDistance="0" geometryGenerator="" overrunDistance="0" offsetType="0" maximumDistanceUnit="MM" allowDegraded="0" polygonPlacementFlags="2" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" lineAnchorClipping="0" fitInPolygonOnly="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" overlapHandling="PreventOverlap" dist="1.3" placement="6" centroidInside="0" overrunDistanceUnit="MM" maxCurvedCharAngleOut="-25" geometryGeneratorEnabled="0" layerType="UnknownGeometry" prioritization="PreferCloser" centroidWhole="0" yOffset="0" offsetUnits="MM" lineAnchorPercent="0.5" quadOffset="4" geometryGeneratorType="PointGeometry" maxCurvedCharAngleIn="25" distUnits="MM" preserveRotation="1" repeatDistance="0" distMapUnitScale="3x:0,0,0,0,0,0" maximumDistanceMapUnitScale="3x:0,0,0,0,0,0" lineAnchorTextPoint="FollowPlacement" priority="7" rotationAngle="0" xOffset="0" placementFlags="10" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" lineAnchorType="0" repeatDistanceUnits="MM" rotationUnit="AngleDegrees"/>
          <rendering minFeatureSize="0" obstacleType="1" fontLimitPixelSize="0" obstacle="1" limitNumLabels="0" fontMaxPixelSize="10000" scaleMax="0" fontMinPixelSize="0" drawLabels="1" zIndex="0" labelPerPart="0" maxNumLabels="2000" upsidedownLabels="0" obstacleFactor="1" scaleMin="0" scaleVisibility="0" mergeLines="0" unplacedVisibility="0"/>
          <dd_properties>
            <Option type="Map">
              <Option type="QString" value="" name="name"/>
              <Option type="Map" name="properties">
                <Option type="Map" name="Size">
                  <Option type="bool" value="true" name="active"/>
                  <Option type="QString" value="CASE WHEN @map_scale &lt; @scialpinismo_scale_12_13 AND @map_scale >= @scialpinismo_scale_15_16 THEN 13.75 ELSE 11 END" name="expression"/>
                  <Option type="int" value="3" name="type"/>
                </Option>
              </Option>
              <Option type="QString" value="collection" name="type"/>
            </Option>
          </dd_properties>
          <callout type="simple">
            <Option type="Map">
              <Option type="QString" value="pole_of_inaccessibility" name="anchorPoint"/>
              <Option type="int" value="0" name="blendMode"/>
              <Option type="Map" name="ddProperties">
                <Option type="QString" value="" name="name"/>
                <Option name="properties"/>
                <Option type="QString" value="collection" name="type"/>
              </Option>
              <Option type="bool" value="false" name="drawToAllParts"/>
              <Option type="QString" value="0" name="enabled"/>
              <Option type="QString" value="point_on_exterior" name="labelAnchorPoint"/>
              <Option type="QString" value="&lt;symbol alpha=&quot;1&quot; type=&quot;line&quot; is_animated=&quot;0&quot; name=&quot;symbol&quot; clip_to_extent=&quot;1&quot; frame_rate=&quot;10&quot; force_rhr=&quot;0&quot;>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;collection&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;layer class=&quot;SimpleLine&quot; locked=&quot;0&quot; pass=&quot;0&quot; enabled=&quot;1&quot; id=&quot;{8a1fcc10-4d52-4b3c-8ace-4bc67e6f7660}&quot;>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;align_dash_pattern&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;square&quot; name=&quot;capstyle&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;5;2&quot; name=&quot;customdash&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;customdash_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;customdash_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;dash_pattern_offset&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;dash_pattern_offset_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;dash_pattern_offset_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;draw_inside_polygon&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;bevel&quot; name=&quot;joinstyle&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;60,60,60,255,rgb:0.2352941,0.2352941,0.2352941,1&quot; name=&quot;line_color&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;solid&quot; name=&quot;line_style&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0.3&quot; name=&quot;line_width&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;line_width_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;offset&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;offset_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;offset_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;ring_filter&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;trim_distance_end&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;trim_distance_end_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;trim_distance_end_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;trim_distance_start&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;trim_distance_start_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;trim_distance_start_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;tweak_dash_pattern_on_corners&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;use_custom_dash&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;width_map_unit_scale&quot;/>&lt;/Option>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;collection&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>" name="lineSymbol"/>
              <Option type="double" value="0" name="minLength"/>
              <Option type="QString" value="3x:0,0,0,0,0,0" name="minLengthMapUnitScale"/>
              <Option type="QString" value="MM" name="minLengthUnit"/>
              <Option type="double" value="0" name="offsetFromAnchor"/>
              <Option type="QString" value="3x:0,0,0,0,0,0" name="offsetFromAnchorMapUnitScale"/>
              <Option type="QString" value="MM" name="offsetFromAnchorUnit"/>
              <Option type="double" value="0" name="offsetFromLabel"/>
              <Option type="QString" value="3x:0,0,0,0,0,0" name="offsetFromLabelMapUnitScale"/>
              <Option type="QString" value="MM" name="offsetFromLabelUnit"/>
            </Option>
          </callout>
        </settings>
      </rule>
    </rules>
  </labeling>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerGeometryType>0</layerGeometryType>
</qgis>
