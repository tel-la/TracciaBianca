<!DOCTYPE qgis PUBLIC 'http://mrcc.com/qgis.dtd' 'SYSTEM'>
<qgis version="3.44.14-Solothurn" labelsEnabled="1" styleCategories="Symbology|Labeling">
  <renderer-v2 type="RuleRenderer" referencescale="-1" forceraster="0" symbollevels="1" enableorderby="0">
    <rules key="{ba353527-6bbf-4af3-8889-1f36bee26819}">
      <rule symbol="0" label="Funivia (va e vieni)" key="{170fe417-4022-4ed4-9ade-ee249adeb64b}" filter="&quot;aerialway&quot; IN ('cable_car','cablecar')"/>
      <rule symbol="1" label="Cabinovia" key="{fc586659-06db-48aa-b172-c420a542d53e}" filter="&quot;aerialway&quot; IN ('gondola','mixed_lift')"/>
      <rule symbol="2" label="Seggiovia" key="{cb018c8e-1ec2-43ea-b92c-880694428b4e}" filter="&quot;aerialway&quot; = 'chair_lift'"/>
      <rule symbol="3" label="Skilift / sciovia" key="{bf25ef01-7927-4733-83bf-5e3379929811}" filter="&quot;aerialway&quot; IN ('drag_lift','t-bar','j-bar','platter','rope_tow')"/>
      <rule symbol="4" label="Teleferica" key="{b6bf64fd-94c9-44ef-8ce4-3790b13e1510}" filter="&quot;aerialway&quot; = 'goods'"/>
      <rule symbol="5" label="Altri impianti" key="{6d8a384e-54c3-4283-9a11-4a4bc8d1cb9b}" else="1"/>
    </rules>
    <symbols>
      <!-- Funivia: doppia fune nera/rossa e cabine grandi. -->
      <symbol type="line" name="0" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10">
        <layer pass="0" class="SimpleLine" locked="0" enabled="1" id="{01a986b4-889c-42ad-8c6f-96b7da64b9ca}"><Option type="Map"><Option type="QString" name="line_color" value="255,254,250,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.66"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/><Option type="QString" name="offset" value="0"/><Option type="QString" name="offset_unit" value="MM"/></Option></layer>
        <layer pass="1" class="SimpleLine" locked="0" enabled="1" id="{073820b8-d26a-4f63-9f95-d13796bfa69c}"><Option type="Map"><Option type="QString" name="line_color" value="48,43,50,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.18"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/><Option type="QString" name="offset" value="-0.16"/><Option type="QString" name="offset_unit" value="MM"/></Option></layer>
        <layer pass="1" class="SimpleLine" locked="0" enabled="1" id="{89555a9b-a7f9-49b1-ad38-6e4cda202a9e}"><Option type="Map"><Option type="QString" name="line_color" value="185,71,71,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.18"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/><Option type="QString" name="offset" value="0.16"/><Option type="QString" name="offset_unit" value="MM"/></Option></layer>
        <layer pass="2" class="MarkerLine" locked="0" enabled="1" id="{7272e91e-eac9-45fd-be9d-2638614187b8}">
          <Option type="Map"><Option type="QString" name="interval" value="8"/><Option type="QString" name="interval_unit" value="MM"/><Option type="QString" name="offset" value="0"/><Option type="QString" name="offset_unit" value="MM"/><Option type="QString" name="offset_along_line" value="0"/><Option type="QString" name="offset_along_line_unit" value="MM"/><Option type="bool" name="place_on_every_part" value="true"/><Option type="QString" name="placements" value="Interval"/><Option type="QString" name="rotate" value="1"/></Option>
          <symbol type="marker" name="@0@3" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10"><layer pass="2" class="SimpleMarker" locked="0" enabled="1" id="{ec4e2701-8a86-48cb-9226-ee251948bf10}"><Option type="Map"><Option type="QString" name="angle" value="0"/><Option type="QString" name="color" value="255,254,250,255"/><Option type="QString" name="name" value="square"/><Option type="QString" name="offset" value="0,0"/><Option type="QString" name="offset_unit" value="MM"/><Option type="QString" name="outline_color" value="48,43,50,255"/><Option type="QString" name="outline_style" value="solid"/><Option type="QString" name="outline_width" value="0.20"/><Option type="QString" name="outline_width_unit" value="MM"/><Option type="QString" name="scale_method" value="diameter"/><Option type="QString" name="size" value="1.35"/><Option type="QString" name="size_unit" value="MM"/></Option></layer></symbol>
        </layer>
      </symbol>
      <!-- Cabinovia: fune continua con cabine chiuse vuote. -->
      <symbol type="line" name="1" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10">
        <layer pass="0" class="SimpleLine" locked="0" enabled="1" id="{a6ba0ea3-9d2f-4758-8f50-fdc1498520e3}"><Option type="Map"><Option type="QString" name="line_color" value="255,254,250,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.50"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
        <layer pass="1" class="SimpleLine" locked="0" enabled="1" id="{0fc3c4a0-e10c-4db0-a7b7-39e59db70c7b}"><Option type="Map"><Option type="QString" name="line_color" value="104,84,119,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.24"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
        <layer pass="2" class="MarkerLine" locked="0" enabled="1" id="{707b5f4e-c690-49f7-80ab-af56964753e9}"><Option type="Map"><Option type="QString" name="interval" value="5.5"/><Option type="QString" name="interval_unit" value="MM"/><Option type="bool" name="place_on_every_part" value="true"/><Option type="QString" name="placements" value="Interval"/><Option type="QString" name="rotate" value="1"/></Option><symbol type="marker" name="@1@2" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10"><layer pass="2" class="SimpleMarker" locked="0" enabled="1" id="{3c25c500-52b8-4bf5-97a7-5930fcd077e7}"><Option type="Map"><Option type="QString" name="angle" value="0"/><Option type="QString" name="color" value="255,254,250,255"/><Option type="QString" name="name" value="square"/><Option type="QString" name="outline_color" value="104,84,119,255"/><Option type="QString" name="outline_style" value="solid"/><Option type="QString" name="outline_width" value="0.20"/><Option type="QString" name="outline_width_unit" value="MM"/><Option type="QString" name="scale_method" value="diameter"/><Option type="QString" name="size" value="0.95"/><Option type="QString" name="size_unit" value="MM"/></Option></layer></symbol></layer>
      </symbol>
      <!-- Seggiovia: seggiole piene a passo regolare. -->
      <symbol type="line" name="2" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10">
        <layer pass="0" class="SimpleLine" locked="0" enabled="1" id="{d14cda85-0414-4856-bdd8-a0e1f83f667d}"><Option type="Map"><Option type="QString" name="line_color" value="255,254,250,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.47"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
        <layer pass="1" class="SimpleLine" locked="0" enabled="1" id="{eac771d6-40bc-443f-958e-062153316ca0}"><Option type="Map"><Option type="QString" name="line_color" value="117,100,129,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.25"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
        <layer pass="2" class="MarkerLine" locked="0" enabled="1" id="{69283990-4888-4cfb-907e-b67cff5cd6bf}"><Option type="Map"><Option type="QString" name="interval" value="4.5"/><Option type="QString" name="interval_unit" value="MM"/><Option type="bool" name="place_on_every_part" value="true"/><Option type="QString" name="placements" value="Interval"/><Option type="QString" name="rotate" value="1"/></Option><symbol type="marker" name="@2@2" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10"><layer pass="2" class="SimpleMarker" locked="0" enabled="1" id="{d361030f-f108-4523-aa21-bc42a261928c}"><Option type="Map"><Option type="QString" name="angle" value="0"/><Option type="QString" name="color" value="117,100,129,255"/><Option type="QString" name="name" value="rounded_square"/><Option type="QString" name="outline_color" value="255,254,250,255"/><Option type="QString" name="outline_style" value="solid"/><Option type="QString" name="outline_width" value="0.12"/><Option type="QString" name="outline_width_unit" value="MM"/><Option type="QString" name="scale_method" value="diameter"/><Option type="QString" name="size" value="0.82"/><Option type="QString" name="size_unit" value="MM"/></Option></layer></symbol></layer>
      </symbol>
      <!-- Sciovia: piccoli piattelli/ancore solo su un lato della fune. -->
      <symbol type="line" name="3" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10">
        <layer pass="0" class="SimpleLine" locked="0" enabled="1" id="{c4c09822-5584-4bef-9dce-45883961c560}"><Option type="Map"><Option type="QString" name="line_color" value="255,254,250,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.45"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
        <layer pass="1" class="SimpleLine" locked="0" enabled="1" id="{bb86bfef-8ed7-4466-bb42-796fb65a0954}"><Option type="Map"><Option type="QString" name="line_color" value="48,43,50,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.22"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
        <layer pass="2" class="MarkerLine" locked="0" enabled="1" id="{f20d61a2-4462-435a-8211-47d17cb742cf}"><Option type="Map"><Option type="QString" name="interval" value="3.6"/><Option type="QString" name="interval_unit" value="MM"/><Option type="bool" name="place_on_every_part" value="true"/><Option type="QString" name="placements" value="Interval"/><Option type="QString" name="rotate" value="1"/></Option><symbol type="marker" name="@3@2" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10"><layer pass="2" class="SimpleMarker" locked="0" enabled="1" id="{a45b4b55-186b-4c0b-9052-30dc2b6bad6c}"><Option type="Map"><Option type="QString" name="angle" value="0"/><Option type="QString" name="color" value="48,43,50,255"/><Option type="QString" name="name" value="line"/><Option type="QString" name="offset" value="0,0.38"/><Option type="QString" name="offset_unit" value="MM"/><Option type="QString" name="outline_color" value="48,43,50,255"/><Option type="QString" name="outline_style" value="solid"/><Option type="QString" name="outline_width" value="0.18"/><Option type="QString" name="outline_width_unit" value="MM"/><Option type="QString" name="scale_method" value="diameter"/><Option type="QString" name="size" value="0.78"/><Option type="QString" name="size_unit" value="MM"/></Option></layer></symbol></layer>
      </symbol>
      <!-- Teleferica merci: fune con croci diagonali. -->
      <symbol type="line" name="4" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10">
        <layer pass="0" class="SimpleLine" locked="0" enabled="1" id="{9f2be2a9-9556-4bc1-aecc-93d61dde92ea}"><Option type="Map"><Option type="QString" name="line_color" value="255,254,250,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.45"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
        <layer pass="1" class="SimpleLine" locked="0" enabled="1" id="{03eb2bb6-e320-4811-b592-889201703ada}"><Option type="Map"><Option type="QString" name="line_color" value="82,73,88,255"/><Option type="QString" name="line_style" value="solid"/><Option type="QString" name="line_width" value="0.21"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
        <layer pass="2" class="MarkerLine" locked="0" enabled="1" id="{dc6c1ba8-b560-4dc2-81e1-c71fd30772f5}"><Option type="Map"><Option type="QString" name="interval" value="4.3"/><Option type="QString" name="interval_unit" value="MM"/><Option type="bool" name="place_on_every_part" value="true"/><Option type="QString" name="placements" value="Interval"/><Option type="QString" name="rotate" value="1"/></Option><symbol type="marker" name="@4@2" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10"><layer pass="2" class="SimpleMarker" locked="0" enabled="1" id="{00dbd3e6-8b97-44fc-b2fc-43e652d6e08f}"><Option type="Map"><Option type="QString" name="angle" value="0"/><Option type="QString" name="color" value="82,73,88,255"/><Option type="QString" name="name" value="cross2"/><Option type="QString" name="outline_color" value="82,73,88,255"/><Option type="QString" name="outline_style" value="solid"/><Option type="QString" name="outline_width" value="0.16"/><Option type="QString" name="outline_width_unit" value="MM"/><Option type="QString" name="scale_method" value="diameter"/><Option type="QString" name="size" value="0.78"/><Option type="QString" name="size_unit" value="MM"/></Option></layer></symbol></layer>
      </symbol>
      <!-- Fallback prudente per valori OSM futuri o non standard. -->
      <symbol type="line" name="5" alpha="1" clip_to_extent="1" force_rhr="0" is_animated="0" frame_rate="10">
        <layer pass="0" class="SimpleLine" locked="0" enabled="1" id="{36f5306e-d5a0-4b9e-8334-6a76fe210102}"><Option type="Map"><Option type="QString" name="line_color" value="255,254,250,255"/><Option type="QString" name="line_style" value="dash"/><Option type="QString" name="line_width" value="0.47"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
        <layer pass="1" class="SimpleLine" locked="0" enabled="1" id="{676f3e52-70a3-45c8-a0f9-17bac718a172}"><Option type="Map"><Option type="QString" name="line_color" value="117,100,129,255"/><Option type="QString" name="line_style" value="dash"/><Option type="QString" name="line_width" value="0.27"/><Option type="QString" name="line_width_unit" value="MM"/><Option type="QString" name="capstyle" value="round"/><Option type="QString" name="joinstyle" value="round"/></Option></layer>
      </symbol>
    </symbols>
    <data-defined-properties><Option type="Map"><Option type="QString" name="name" value=""/><Option name="properties"/><Option type="QString" name="type" value="collection"/></Option></data-defined-properties>
  </renderer-v2>
  <selection mode="Default">
    <selectionColor invalid="1"/>
  </selection>
  <labeling type="simple">
    <settings calloutType="simple">
      <text-style fontFamily="Arial" fontWeight="75" forcedBold="0" fontKerning="1" fontSizeUnit="Point" fontSize="10.199999999999999" multilineHeightUnit="Percentage" textOrientation="horizontal" fontLetterSpacing="0" blendMode="0" capitalization="0" useSubstitutions="0" fontWordSpacing="0" isExpression="1" fontSizeMapUnitScale="3x:0,0,0,0,0,0" allowHtml="0" fontStrikeout="0" forcedItalic="0" previewBkgrdColor="255,255,255,255,rgb:1,1,1,1" textOpacity="1" tabStopDistance="6" fontUnderline="0" tabStopDistanceUnit="Percentage" multilineHeight="1" fieldName="coalesce(nullif(&quot;label&quot;,''),nullif(&quot;ref&quot;,''))" legendString="Aa" fontItalic="0" textColor="85,64,97,255,rgb:0.3333333,0.2509804,0.3803922,1" namedStyle="" tabStopDistanceMapUnitScale="3x:0,0,0,0,0,0">
        <families/>
        <text-buffer bufferDraw="1" bufferSizeMapUnitScale="3x:0,0,0,0,0,0" bufferBlendMode="0" bufferOpacity="1" bufferSizeUnits="MM" bufferJoinStyle="128" bufferColor="255,254,250,255,rgb:1,0.9960784,0.9803922,1" bufferNoFill="1" bufferSize="0.71999999999999997"/>
        <text-mask maskOpacity="1" maskedSymbolLayers="" maskType="0" maskSizeMapUnitScale="3x:0,0,0,0,0,0" maskEnabled="0" maskSize="1.5" maskSizeUnits="MM" maskJoinStyle="128" maskSize2="1.5"/>
        <background shapeSizeMapUnitScale="3x:0,0,0,0,0,0" shapeSVGFile="" shapeOffsetMapUnitScale="3x:0,0,0,0,0,0" shapeBlendMode="0" shapeOffsetX="0" shapeFillColor="255,255,255,255,rgb:1,1,1,1" shapeOffsetY="0" shapeRotationType="0" shapeType="0" shapeBorderWidthUnit="MM" shapeBorderWidth="0" shapeSizeUnit="MM" shapeSizeType="0" shapeOffsetUnit="MM" shapeRadiiX="0" shapeRadiiY="0" shapeOpacity="1" shapeJoinStyle="64" shapeBorderColor="128,128,128,255,rgb:0.5019608,0.5019608,0.5019608,1" shapeRadiiUnit="MM" shapeDraw="0" shapeBorderWidthMapUnitScale="3x:0,0,0,0,0,0" shapeSizeX="0" shapeSizeY="0" shapeRotation="0" shapeRadiiMapUnitScale="3x:0,0,0,0,0,0">
          <symbol type="fill" is_animated="0" clip_to_extent="1" name="fillSymbol" alpha="1" frame_rate="10" force_rhr="0">
            <data_defined_properties>
              <Option type="Map">
                <Option type="QString" name="name" value=""/>
                <Option name="properties"/>
                <Option type="QString" name="type" value="collection"/>
              </Option>
            </data_defined_properties>
            <layer pass="0" class="SimpleFill" locked="0" enabled="1" id="">
              <Option type="Map">
                <Option type="QString" name="border_width_map_unit_scale" value="3x:0,0,0,0,0,0"/>
                <Option type="QString" name="color" value="255,255,255,255,rgb:1,1,1,1"/>
                <Option type="QString" name="joinstyle" value="bevel"/>
                <Option type="QString" name="offset" value="0,0"/>
                <Option type="QString" name="offset_map_unit_scale" value="3x:0,0,0,0,0,0"/>
                <Option type="QString" name="offset_unit" value="MM"/>
                <Option type="QString" name="outline_color" value="128,128,128,255,rgb:0.5019608,0.5019608,0.5019608,1"/>
                <Option type="QString" name="outline_style" value="no"/>
                <Option type="QString" name="outline_width" value="0"/>
                <Option type="QString" name="outline_width_unit" value="MM"/>
                <Option type="QString" name="style" value="solid"/>
              </Option>
              <data_defined_properties>
                <Option type="Map">
                  <Option type="QString" name="name" value=""/>
                  <Option name="properties"/>
                  <Option type="QString" name="type" value="collection"/>
                </Option>
              </data_defined_properties>
            </layer>
          </symbol>
        </background>
        <shadow shadowRadiusMapUnitScale="3x:0,0,0,0,0,0" shadowUnder="0" shadowColor="0,0,0,255,rgb:0,0,0,1" shadowBlendMode="6" shadowOffsetAngle="135" shadowOffsetMapUnitScale="3x:0,0,0,0,0,0" shadowOffsetDist="1" shadowOffsetGlobal="1" shadowRadius="1.5" shadowRadiusAlphaOnly="0" shadowScale="100" shadowRadiusUnit="MM" shadowOpacity="0.69999999999999996" shadowOffsetUnit="MM" shadowDraw="0"/>
        <dd_properties>
          <Option type="Map">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
        </dd_properties>
        <substitutions/>
      </text-style>
      <text-format leftDirectionSymbol="&lt;" rightDirectionSymbol=">" autoWrapLength="0" reverseDirectionSymbol="0" useMaxLineLengthForAutoWrap="1" addDirectionSymbol="0" decimals="3" wrapChar="" formatNumbers="0" multilineAlign="3" placeDirectionSymbol="0" plussign="0"/>
      <placement overrunDistanceMapUnitScale="3x:0,0,0,0,0,0" offsetType="0" layerType="UnknownGeometry" preserveRotation="1" xOffset="0" overrunDistanceUnit="MM" distMapUnitScale="3x:0,0,0,0,0,0" maximumDistance="0" geometryGeneratorType="PointGeometry" repeatDistanceUnits="MM" lineAnchorPercent="0.5" polygonPlacementFlags="2" rotationAngle="0" labelOffsetMapUnitScale="3x:0,0,0,0,0,0" maxCurvedCharAngleIn="25" priority="7" placementFlags="10" predefinedPositionOrder="TR,TL,BR,BL,R,L,TSR,BSR" lineAnchorType="0" offsetUnits="MM" allowDegraded="0" lineAnchorTextPoint="FollowPlacement" fitInPolygonOnly="0" lineAnchorClipping="0" quadOffset="4" maximumDistanceMapUnitScale="3x:0,0,0,0,0,0" repeatDistanceMapUnitScale="3x:0,0,0,0,0,0" geometryGeneratorEnabled="0" yOffset="0" overrunDistance="0" geometryGenerator="" repeatDistance="100" centroidWhole="0" rotationUnit="AngleDegrees" centroidInside="0" maximumDistanceUnit="MM" maxCurvedCharAngleOut="-25" dist="1" distUnits="MM" prioritization="PreferCloser" overlapHandling="PreventOverlap" placement="2"/>
      <rendering fontMaxPixelSize="10000" mergeLines="0" obstacleFactor="1" scaleVisibility="0" labelPerPart="0" fontMinPixelSize="0" maxNumLabels="2000" upsidedownLabels="0" drawLabels="1" unplacedVisibility="0" minFeatureSize="0" scaleMax="0" limitNumLabels="0" obstacle="1" obstacleType="1" fontLimitPixelSize="0" zIndex="0" scaleMin="0"/>
      <dd_properties>
        <Option type="Map">
          <Option type="QString" name="name" value=""/>
          <Option name="properties"/>
          <Option type="QString" name="type" value="collection"/>
        </Option>
      </dd_properties>
      <callout type="simple">
        <Option type="Map">
          <Option type="QString" name="anchorPoint" value="pole_of_inaccessibility"/>
          <Option type="int" name="blendMode" value="0"/>
          <Option type="Map" name="ddProperties">
            <Option type="QString" name="name" value=""/>
            <Option name="properties"/>
            <Option type="QString" name="type" value="collection"/>
          </Option>
          <Option type="bool" name="drawToAllParts" value="false"/>
          <Option type="QString" name="enabled" value="0"/>
          <Option type="QString" name="labelAnchorPoint" value="point_on_exterior"/>
          <Option type="QString" name="lineSymbol" value="&lt;symbol type=&quot;line&quot; is_animated=&quot;0&quot; clip_to_extent=&quot;1&quot; name=&quot;symbol&quot; alpha=&quot;1&quot; frame_rate=&quot;10&quot; force_rhr=&quot;0&quot;>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; name=&quot;name&quot; value=&quot;&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;type&quot; value=&quot;collection&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;layer pass=&quot;0&quot; class=&quot;SimpleLine&quot; locked=&quot;0&quot; enabled=&quot;1&quot; id=&quot;{c14a8b20-8f52-42d6-8f6e-6c3f03c92f6d}&quot;>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; name=&quot;align_dash_pattern&quot; value=&quot;0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;capstyle&quot; value=&quot;square&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;customdash&quot; value=&quot;5;2&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;customdash_map_unit_scale&quot; value=&quot;3x:0,0,0,0,0,0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;customdash_unit&quot; value=&quot;MM&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;dash_pattern_offset&quot; value=&quot;0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;dash_pattern_offset_map_unit_scale&quot; value=&quot;3x:0,0,0,0,0,0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;dash_pattern_offset_unit&quot; value=&quot;MM&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;draw_inside_polygon&quot; value=&quot;0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;joinstyle&quot; value=&quot;bevel&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;line_color&quot; value=&quot;60,60,60,255,rgb:0.2352941,0.2352941,0.2352941,1&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;line_style&quot; value=&quot;solid&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;line_width&quot; value=&quot;0.3&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;line_width_unit&quot; value=&quot;MM&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;offset&quot; value=&quot;0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;offset_map_unit_scale&quot; value=&quot;3x:0,0,0,0,0,0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;offset_unit&quot; value=&quot;MM&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;ring_filter&quot; value=&quot;0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;trim_distance_end&quot; value=&quot;0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;trim_distance_end_map_unit_scale&quot; value=&quot;3x:0,0,0,0,0,0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;trim_distance_end_unit&quot; value=&quot;MM&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;trim_distance_start&quot; value=&quot;0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;trim_distance_start_map_unit_scale&quot; value=&quot;3x:0,0,0,0,0,0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;trim_distance_start_unit&quot; value=&quot;MM&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;tweak_dash_pattern_on_corners&quot; value=&quot;0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;use_custom_dash&quot; value=&quot;0&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;width_map_unit_scale&quot; value=&quot;3x:0,0,0,0,0,0&quot;/>&lt;/Option>&lt;data_defined_properties>&lt;Option type=&quot;Map&quot;>&lt;Option type=&quot;QString&quot; name=&quot;name&quot; value=&quot;&quot;/>&lt;Option name=&quot;properties&quot;/>&lt;Option type=&quot;QString&quot; name=&quot;type&quot; value=&quot;collection&quot;/>&lt;/Option>&lt;/data_defined_properties>&lt;/layer>&lt;/symbol>"/>
          <Option type="double" name="minLength" value="0"/>
          <Option type="QString" name="minLengthMapUnitScale" value="3x:0,0,0,0,0,0"/>
          <Option type="QString" name="minLengthUnit" value="MM"/>
          <Option type="double" name="offsetFromAnchor" value="0"/>
          <Option type="QString" name="offsetFromAnchorMapUnitScale" value="3x:0,0,0,0,0,0"/>
          <Option type="QString" name="offsetFromAnchorUnit" value="MM"/>
          <Option type="double" name="offsetFromLabel" value="0"/>
          <Option type="QString" name="offsetFromLabelMapUnitScale" value="3x:0,0,0,0,0,0"/>
          <Option type="QString" name="offsetFromLabelUnit" value="MM"/>
        </Option>
      </callout>
    </settings>
  </labeling>
  <blendMode>0</blendMode>
  <featureBlendMode>0</featureBlendMode>
  <layerGeometryType>1</layerGeometryType>
</qgis>
