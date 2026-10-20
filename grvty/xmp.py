"""Writing a look as a Lightroom preset (.xmp), the format Lightroom Classic,
Lightroom and Camera Raw all read from %APPDATA%\\Adobe\\CameraRaw\\Settings."""
import os
import re
import uuid
from pathlib import Path
from xml.sax.saxutils import escape

from .params import HUES, merge

LR_HUE = {h: h.capitalize() for h in HUES}


def preset_xml(name, params, group="Grvty"):
    p = merge(params)
    a = {}
    a["Exposure2012"] = f"{p['exposure']:+.2f}"
    for k, lr in (("contrast", "Contrast2012"), ("highlights", "Highlights2012"), ("shadows", "Shadows2012"),
                  ("whites", "Whites2012"), ("blacks", "Blacks2012"), ("texture", "Texture"),
                  ("clarity", "Clarity2012"), ("vibrance", "Vibrance"), ("saturation", "Saturation")):
        a[lr] = f"{round(p[k]):+d}"
    if p["temp"] or p["tint"]:
        # relative white balance (Lightroom applies this to JPEG/TIFF; RAW uses absolute Kelvin)
        a["IncrementalTemperature"] = f"{round(p['temp']):+d}"
        a["IncrementalTint"] = f"{round(p['tint']):+d}"
    for h in HUES:
        H = LR_HUE[h]
        a[f"HueAdjustment{H}"] = f"{round(p['hsl_hue'][h]):+d}"
        a[f"SaturationAdjustment{H}"] = f"{round(p['hsl_sat'][h]):+d}"
        a[f"LuminanceAdjustment{H}"] = f"{round(p['hsl_lum'][h]):+d}"
        a[f"GrayMixer{H}"] = f"{round(p['bw_mix'][h]):+d}"
    a["ConvertToGrayscale"] = "True" if p["bw"] else "False"
    g = p["grade"]
    for z, lr in (("shadows", "Shadow"), ("midtones", "Midtone"), ("highlights", "Highlight"), ("global", "Global")):
        a[f"ColorGrade{lr}Hue"] = str(round(g[z]["hue"]) % 360)
        a[f"ColorGrade{lr}Sat"] = str(round(g[z]["sat"]))
        a[f"ColorGrade{lr}Lum"] = f"{round(g[z]['lum']):+d}"
    a["ColorGradeBlending"] = str(round(g["blending"]))
    a["SplitToningBalance"] = f"{round(g['balance']):+d}"
    # older Lightroom versions read split toning instead of colour grading
    a["SplitToningShadowHue"], a["SplitToningShadowSaturation"] = str(round(g["shadows"]["hue"]) % 360), str(round(g["shadows"]["sat"]))
    a["SplitToningHighlightHue"], a["SplitToningHighlightSaturation"] = str(round(g["highlights"]["hue"]) % 360), str(round(g["highlights"]["sat"]))
    a["PostCropVignetteAmount"] = f"{round(p['vignette']):+d}"
    a["PostCropVignetteMidpoint"] = str(round(p["vignette_mid"]))
    a["PostCropVignetteFeather"] = str(round(p["vignette_feather"]))
    a["PostCropVignetteStyle"] = "1"
    a["GrainAmount"] = str(round(p["grain"]))
    a["GrainSize"] = str(round(p["grain_size"]))
    a["GrainFrequency"] = "50"
    a["ToneCurveName2012"] = "Custom" if p["curve"] != [[0, 0], [255, 255]] else "Linear"

    attrs = "\n".join(f'   crs:{k}="{v}"' for k, v in a.items())
    curve = "\n".join(f"      <rdf:li>{round(x)}, {round(y)}</rdf:li>" for x, y in p["curve"])
    lin = "\n".join(f"      <rdf:li>{v}, {v}</rdf:li>" for v in (0, 255))
    def seq(tag, body):
        return f"   <crs:{tag}>\n    <rdf:Seq>\n{body}\n    </rdf:Seq>\n   </crs:{tag}>"
    curves = "\n".join([seq("ToneCurvePV2012", curve)] + [seq(f"ToneCurvePV2012{c}", lin) for c in ("Red", "Green", "Blue")])
    nm = escape(name)
    return f'''<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="Grvty">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description rdf:about=""
   xmlns:crs="http://ns.adobe.com/camera-raw-settings/1.0/"
   crs:PresetType="Normal"
   crs:Cluster=""
   crs:UUID="{uuid.uuid4().hex.upper()}"
   crs:SupportsAmount="True"
   crs:SupportsColor="True"
   crs:SupportsMonochrome="True"
   crs:SupportsHighDynamicRange="True"
   crs:SupportsNormalDynamicRange="True"
   crs:SupportsSceneReferred="True"
   crs:SupportsOutputReferred="True"
   crs:CameraModelRestriction=""
   crs:Copyright=""
   crs:ContactInfo=""
   crs:Version="15.0"
   crs:ProcessVersion="11.0"
   crs:HasSettings="True"
{attrs}>
   <crs:Name>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{nm}</rdf:li>
    </rdf:Alt>
   </crs:Name>
   <crs:Group>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">{escape(group)}</rdf:li>
    </rdf:Alt>
   </crs:Group>
{curves}
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>
'''


def lightroom_preset_dir():
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Adobe" / "CameraRaw" / "Settings" / "Grvty"
    return Path.home() / "Library" / "Application Support" / "Adobe" / "CameraRaw" / "Settings" / "Grvty"


def save_preset(name, params, backup_dir):
    safe = re.sub(r'[<>:"/\\|?*]+', "", name).strip() or "Grvty look"
    xml = preset_xml(safe, params)
    written = []
    for folder in (lightroom_preset_dir(), Path(backup_dir)):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{safe}.xmp"
            i = 2
            while path.exists():
                path = folder / f"{safe} ({i}).xmp"
                i += 1
            path.write_text(xml, encoding="utf-8")
            written.append(str(path))
        except OSError:
            pass
    return written
