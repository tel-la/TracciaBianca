<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis labelsEnabled="1" styleCategories="Symbology|Labeling" version="3.44.14-Solothurn">
  <renderer-v2 referencescale="-1" type="RuleRenderer" forceraster="0" symbollevels="0" enableorderby="0">
    <rules key="{9ac1c427-8e2a-425e-b4ff-df30f1b6b75e}">
      <rule filter="(&quot;place&quot; IN ('town','village') OR (&quot;place&quot; = 'hamlet' AND @map_scale &lt; @scialpinismo_scale_13_14) OR (&quot;natural&quot; = 'peak' AND to_real(&quot;ele&quot;) >= CASE WHEN @map_scale > 2 * @scialpinismo_scale_13_14 THEN 3000 ELSE 2600 END)) AND &quot;natural&quot; = 'peak'" key="{1dd207da-d05c-45f5-98d6-c799e6807449}" symbol="0" label="Vette"/>
      <rule filter="(&quot;place&quot; IN ('town','village') OR (&quot;place&quot; = 'hamlet' AND @map_scale &lt; @scialpinismo_scale_13_14) OR (&quot;natural&quot; = 'peak' AND to_real(&quot;ele&quot;) >= CASE WHEN @map_scale > 2 * @scialpinismo_scale_13_14 THEN 3000 ELSE 2600 END)) AND &quot;natural&quot; = 'saddle'" key="{55ffb830-f648-4595-8070-9e43cfa627ae}" symbol="1" label="Colli"/>
      <rule filter="&quot;amenity&quot; = 'parking' AND @map_scale &lt; @scialpinismo_scale_13_14" key="{864ecf1e-b2bc-45c1-a0db-200125e8273c}" symbol="2" label="Parcheggi — zoom 14"/>
      <rule filter="(&quot;place&quot; IN ('town','village') OR (&quot;place&quot; = 'hamlet' AND @map_scale &lt; @scialpinismo_scale_13_14) OR (&quot;natural&quot; = 'peak' AND to_real(&quot;ele&quot;) >= CASE WHEN @map_scale > 2 * @scialpinismo_scale_13_14 THEN 3000 ELSE 2600 END)) AND NOT (&quot;natural&quot; IN ('peak','saddle')) AND NOT (&quot;amenity&quot; = 'parking')" key="{1dcac3e0-6567-4ed0-bc55-235dc09b3bfe}" symbol="3" label="Centri abitati e riferimenti"/>
    </rules>
    <symbols>
      <symbol is_animated="0" force_rhr="0" alpha="1" frame_rate="10" type="marker" name="0" clip_to_extent="1">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" value="" name="name"/>
            <Option name="properties"/>
            <Option type="QString" value="collection" name="type"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" locked="0" enabled="1" pass="0" id="{54e8d81c-e99d-4ce4-9d8c-0857ebdd51f8}">
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
      <symbol is_animated="0" force_rhr="0" alpha="1" frame_rate="10" type="marker" name="1" clip_to_extent="1">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" value="" name="name"/>
            <Option name="properties"/>
            <Option type="QString" value="collection" name="type"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" locked="0" enabled="1" pass="0" id="{ea34757a-a1a5-4309-bbc1-5ec95457e6e2}">
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
      <symbol is_animated="0" force_rhr="0" alpha="1" frame_rate="10" type="marker" name="2" clip_to_extent="1">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" value="" name="name"/>
            <Option name="properties"/>
            <Option type="QString" value="collection" name="type"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" locked="0" enabled="1" pass="0" id="{2603747d-fb3a-427c-9ea3-bd16bcca2ddb}">
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
        <layer class="FontMarker" locked="0" enabled="1" pass="0" id="{59ee6fa4-1762-49ab-bbbf-e842c4822e97}">
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
      <symbol is_animated="0" force_rhr="0" alpha="1" frame_rate="10" type="marker" name="3" clip_to_extent="1">
        <data_defined_properties>
          <Option type="Map">
            <Option type="QString" value="" name="name"/>
            <Option name="properties"/>
            <Option type="QString" value="collection" name="type"/>
          </Option>
        </data_defined_properties>
        <layer class="SimpleMarker" locked="0" enabled="1" pass="0" id="{e30a32a6-560a-49cf-bed3-54119ef7c5cf}">
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
    <rules key="{bc7038a1-60c1-49db-b0ec-e084ac558a6a}">
      <rule filter="(&quot;place&quot; IN ('town','village') OR (&quot;place&quot; = 'hamlet' AND @map_scale &lt; @scialpinismo_scale_13_14) OR (&quot;natural&quot; = 'peak' AND to_real(&quot;ele&quot;) >= CASE WHEN @map_scale > 2 * @scialpinismo_scale_13_14 THEN 3000 ELSE 2600 END)) AND (&quot;place&quot; IN ('town','village','hamlet')) AND NOT (&quot;amenity&quot; = 'parking')" key="{0bd054b0-2d6c-463e-874d-b0567e792dd8}">
        <settings calloutType="simple">
          <text-style tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0" fontSize="12.5" allowHtml="0" fontWeight="75" fieldName="&quot;label&quot;" isExpression="1" forcedBold="0" tabStopDistance="6" capitalization="0" multilineHeight="1" useSubstitutions="0" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" multilineHeightUnit="Percentage" forcedItalic="0" textColor="37,37,37,255,rgb:0.145098,0.145098,0.145098,1" textOrientation="horizontal" legendString="Aa" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontItalic="0" textOpacity="1" fontWordSpacing="0" tabStopDistanceUnit="Percentage" fontFamily="Arial" blendMode="0" fontUnderline="0" fontStrikeout="0" namedStyle="" fontLetterSpacing="0" fontKerning="1" fontSizeUnit="Point">
            <families/>
            <text-buffer bufferOpacity="1" bufferBlendMode="0" bufferSize="0.71999999999999997" bufferColor="255,254,250,255,rgb:1,0.9960784,0.9803922,1" bufferDraw="1" bufferNoFill="1" bufferSizeUnits="MM" bufferJoinStyle="128" bufferSizeMapUnitScale="3x:0,0,0,0,0,0"/>
            <text-mask maskSize="1.5" maskSize2="1.5" maskedSymbolLayers="" maskEnabled="0" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskType="0" maskSizeUnits="MM" maskJoinStyle="128" maskOpacity="1"/>
            <background shapeRotation="0" shapeDraw="0" shapeRadiiX="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiY="0" shapeJoinStyle="64" shapeOpacity="1" shapeBorderWidth="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeSizeUnit="MM" shapeRadiiUnit="MM" shapeSVGFile="" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeType="0" shapeOffsetUnit="MM" shapeSizeX="0" shapeBorderColor="128,128,128,255,rgb:0.5019608,0.5019608,0.5019608,1" shapeBorderWidthUnit="MM" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeSizeY="0" shapeRotationType="0" shapeBlendMode="0" shapeFillColor="255,255,255,255,rgb:1,1,1,1" shapeOffsetX="0" shapeOffsetY="0">
              <symbol is_animated="0" force_rhr="0" alpha="1" frame_rate="10" type="fill" name="fillSymbol" clip_to_extent="1">
                <data_defined_properties>
                  <Option type="Map">
                    <Option type="QString" value="" name="name"/>
                    <Option name="properties"/>
                    <Option type="QString" value="collection" name="type"/>
                  </Option>
                </data_defined_properties>
                <layer class="SimpleFill" locked="0" enabled="1" pass="0" id="">
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
            <shadow shadowUnder="0" shadowOffsetAngle="135" shadowRadiusUnit="MM" shadowRadiusAlphaOnly="0" shadowColor="0,0,0,255,rgb:0,0,0,1" shadowOffsetUnit="MM" shadowOffsetGlobal="1" shadowRadius="1.5" shadowScale="100" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowBlendMode="6" shadowDraw="0" shadowOpacity="0.69999999999999996" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetDist="1"/>
            <dd_properties>
              <Option type="Map">
                <Option type="QString" value="" name="name"/>
                <Option name="properties"/>
                <Option type="QString" value="collection" name="type"/>
              </Option>
            </dd_properties>
            <substitutions/>
          </text-style>
          <text-format leftDirectionSymbol="&lt;" placeDirectionSymbol="0" addDirectionSymbol="0" rightDirectionSymbol=">" plussign="0" multilineAlign="3" formatNumbers="0" autoWrapLength="0" decimals="3" useMaxLineLengthForAutoWrap="1" wrapChar="" reverseDirectionSymbol="0"/>
          <placement overrunDistance="0" distMapUnitScale="3x:0,0,0,0,0,0" layerType="UnknownGeometry" repeatDistanceUnits="MM" rotationUnit="AngleDegrees" yOffset="0" geometryGeneratorEnabled="0" maximumDistanceUnit="MM" rotationAngle="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" maximumDistanceMapUnitScale="3x:0,0,0,0,0,0" offsetUnits="MM" geometryGeneratorType="PointGeometry" distUnits="MM" polygonPlacementFlags="2" overrunDistanceUnit="MM" xOffset="0" geometryGenerator="" fitInPolygonOnly="0" placementFlags="10" dist="1.3" maxCurvedCharAngleIn="25" allowDegraded="0" lineAnchorType="0" maxCurvedCharAngleOut="-25" overlapHandling="PreventOverlap" centroidWhole="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" lineAnchorClipping="0" repeatDistance="0" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" lineAnchorTextPoint="FollowPlacement" lineAnchorPercent="0.5" priority="9" centroidInside="0" placement="6" maximumDistance="0" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" offsetType="0" quadOffset="4" preserveRotation="1" prioritization="PreferCloser"/>
          <rendering fontMaxPixelSize="10000" unplacedVisibility="0" minFeatureSize="0" limitNumLabels="0" scaleMax="0" scaleVisibility="0" upsidedownLabels="0" obstacle="1" obstacleType="1" fontLimitPixelSize="0" drawLabels="1" zIndex="0" scaleMin="0" obstacleFactor="1" mergeLines="0" labelPerPart="0" maxNumLabels="2000" fontMinPixelSize="0"/>
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
              <Option type="QString" value="&lt;symbol is_animated=&quot;0&quot; force_rhr=&quot;0&quot; alpha=&quot;1&quot; frame_rate=&quot;10&quot; type=&quot;line&quot; name=&quot;symbol&quot; clip_to_extent=&quot;1&quot;>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;collection&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;layer class=&quot;SimpleLine&quot; locked=&quot;0&quot; enabled=&quot;1&quot; pass=&quot;0&quot; id=&quot;{5ada106f-2710-488d-b52a-785ec3a10b19}&quot;>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;align_dash_pattern&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;square&quot; name=&quot;capstyle&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;5;2&quot; name=&quot;customdash&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;customdash_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;customdash_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;dash_pattern_offset&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;dash_pattern_offset_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;dash_pattern_offset_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;draw_inside_polygon&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;bevel&quot; name=&quot;joinstyle&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;60,60,60,255,rgb:0.2352941,0.2352941,0.2352941,1&quot; name=&quot;line_color&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;solid&quot; name=&quot;line_style&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0.3&quot; name=&quot;line_width&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;line_width_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;offset&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;offset_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;offset_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;ring_filter&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;trim_distance_end&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;trim_distance_end_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;trim_distance_end_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;trim_distance_start&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;trim_distance_start_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;trim_distance_start_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;tweak_dash_pattern_on_corners&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;use_custom_dash&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;width_map_unit_scale&quot;/>&lt;/Option>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;collection&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>" name="lineSymbol"/>
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
      <rule filter="(&quot;place&quot; IN ('town','village') OR (&quot;place&quot; = 'hamlet' AND @map_scale &lt; @scialpinismo_scale_13_14) OR (&quot;natural&quot; = 'peak' AND to_real(&quot;ele&quot;) >= CASE WHEN @map_scale > 2 * @scialpinismo_scale_13_14 THEN 3000 ELSE 2600 END)) AND (NOT (&quot;place&quot; IN ('town','village','hamlet'))) AND NOT (&quot;amenity&quot; = 'parking')" key="{9c7950d0-9536-40a4-9483-cd40fcd25c31}">
        <settings calloutType="simple">
          <text-style tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0" fontSize="11" allowHtml="0" fontWeight="50" fieldName="&quot;label&quot;" isExpression="1" forcedBold="0" tabStopDistance="6" capitalization="0" multilineHeight="1" useSubstitutions="0" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" multilineHeightUnit="Percentage" forcedItalic="0" textColor="37,37,37,255,rgb:0.145098,0.145098,0.145098,1" textOrientation="horizontal" legendString="Aa" fontSizeMapUnitScale="3x:0,0,0,0,0,0" fontItalic="0" textOpacity="1" fontWordSpacing="0" tabStopDistanceUnit="Percentage" fontFamily="Arial" blendMode="0" fontUnderline="0" fontStrikeout="0" namedStyle="" fontLetterSpacing="0" fontKerning="1" fontSizeUnit="Point">
            <families/>
            <text-buffer bufferOpacity="1" bufferBlendMode="0" bufferSize="0.71999999999999997" bufferColor="255,254,250,255,rgb:1,0.9960784,0.9803922,1" bufferDraw="1" bufferNoFill="1" bufferSizeUnits="MM" bufferJoinStyle="128" bufferSizeMapUnitScale="3x:0,0,0,0,0,0"/>
            <text-mask maskSize="1.5" maskSize2="1.5" maskedSymbolLayers="" maskEnabled="0" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskType="0" maskSizeUnits="MM" maskJoinStyle="128" maskOpacity="1"/>
            <background shapeRotation="0" shapeDraw="0" shapeRadiiX="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeRadiiY="0" shapeJoinStyle="64" shapeOpacity="1" shapeBorderWidth="0" shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSizeType="0" shapeSizeUnit="MM" shapeRadiiUnit="MM" shapeSVGFile="" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0" shapeType="0" shapeOffsetUnit="MM" shapeSizeX="0" shapeBorderColor="128,128,128,255,rgb:0.5019608,0.5019608,0.5019608,1" shapeBorderWidthUnit="MM" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeSizeY="0" shapeRotationType="0" shapeBlendMode="0" shapeFillColor="255,255,255,255,rgb:1,1,1,1" shapeOffsetX="0" shapeOffsetY="0">
              <symbol is_animated="0" force_rhr="0" alpha="1" frame_rate="10" type="fill" name="fillSymbol" clip_to_extent="1">
                <data_defined_properties>
                  <Option type="Map">
                    <Option type="QString" value="" name="name"/>
                    <Option name="properties"/>
                    <Option type="QString" value="collection" name="type"/>
                  </Option>
                </data_defined_properties>
                <layer class="SimpleFill" locked="0" enabled="1" pass="0" id="">
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
            <shadow shadowUnder="0" shadowOffsetAngle="135" shadowRadiusUnit="MM" shadowRadiusAlphaOnly="0" shadowColor="0,0,0,255,rgb:0,0,0,1" shadowOffsetUnit="MM" shadowOffsetGlobal="1" shadowRadius="1.5" shadowScale="100" shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowBlendMode="6" shadowDraw="0" shadowOpacity="0.69999999999999996" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetDist="1"/>
            <dd_properties>
              <Option type="Map">
                <Option type="QString" value="" name="name"/>
                <Option name="properties"/>
                <Option type="QString" value="collection" name="type"/>
              </Option>
            </dd_properties>
            <substitutions/>
          </text-style>
          <text-format leftDirectionSymbol="&lt;" placeDirectionSymbol="0" addDirectionSymbol="0" rightDirectionSymbol=">" plussign="0" multilineAlign="3" formatNumbers="0" autoWrapLength="0" decimals="3" useMaxLineLengthForAutoWrap="1" wrapChar="" reverseDirectionSymbol="0"/>
          <placement overrunDistance="0" distMapUnitScale="3x:0,0,0,0,0,0" layerType="UnknownGeometry" repeatDistanceUnits="MM" rotationUnit="AngleDegrees" yOffset="0" geometryGeneratorEnabled="0" maximumDistanceUnit="MM" rotationAngle="0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" maximumDistanceMapUnitScale="3x:0,0,0,0,0,0" offsetUnits="MM" geometryGeneratorType="PointGeometry" distUnits="MM" polygonPlacementFlags="2" overrunDistanceUnit="MM" xOffset="0" geometryGenerator="" fitInPolygonOnly="0" placementFlags="10" dist="1.3" maxCurvedCharAngleIn="25" allowDegraded="0" lineAnchorType="0" maxCurvedCharAngleOut="-25" overlapHandling="PreventOverlap" centroidWhole="0" overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" lineAnchorClipping="0" repeatDistance="0" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" lineAnchorTextPoint="FollowPlacement" lineAnchorPercent="0.5" priority="7" centroidInside="0" placement="6" maximumDistance="0" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" offsetType="0" quadOffset="4" preserveRotation="1" prioritization="PreferCloser"/>
          <rendering fontMaxPixelSize="10000" unplacedVisibility="0" minFeatureSize="0" limitNumLabels="0" scaleMax="0" scaleVisibility="0" upsidedownLabels="0" obstacle="1" obstacleType="1" fontLimitPixelSize="0" drawLabels="1" zIndex="0" scaleMin="0" obstacleFactor="1" mergeLines="0" labelPerPart="0" maxNumLabels="2000" fontMinPixelSize="0"/>
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
              <Option type="QString" value="&lt;symbol is_animated=&quot;0&quot; force_rhr=&quot;0&quot; alpha=&quot;1&quot; frame_rate=&quot;10&quot; type=&quot;line&quot; name=&quot;symbol&quot; clip_to_extent=&quot;1&quot;>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;collection&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;layer class=&quot;SimpleLine&quot; locked=&quot;0&quot; enabled=&quot;1&quot; pass=&quot;0&quot; id=&quot;{4c829c79-a51a-429e-8a08-20f38735c751}&quot;>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;align_dash_pattern&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;square&quot; name=&quot;capstyle&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;5;2&quot; name=&quot;customdash&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;customdash_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;customdash_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;dash_pattern_offset&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;dash_pattern_offset_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;dash_pattern_offset_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;draw_inside_polygon&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;bevel&quot; name=&quot;joinstyle&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;60,60,60,255,rgb:0.2352941,0.2352941,0.2352941,1&quot; name=&quot;line_color&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;solid&quot; name=&quot;line_style&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0.3&quot; name=&quot;line_width&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;line_width_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;offset&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;offset_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;offset_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;ring_filter&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;trim_distance_end&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;trim_distance_end_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;trim_distance_end_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;trim_distance_start&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;trim_distance_start_map_unit_scale&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;MM&quot; name=&quot;trim_distance_start_unit&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;tweak_dash_pattern_on_corners&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;0&quot; name=&quot;use_custom_dash&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;3x:0,0,0,0,0,0&quot; name=&quot;width_map_unit_scale&quot;/>&lt;/Option>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; value=&quot;&quot; name=&quot;name&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; value=&quot;collection&quot; name=&quot;type&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>" name="lineSymbol"/>
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
