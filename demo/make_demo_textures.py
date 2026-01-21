from pathlib import Path
from PIL import Image

def write_png(path: Path, size=(256, 256), mode="RGB"):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new(mode, size).save(path)

def main():
    base = Path(__file__).parent

    write_png(base/"exports_unreal_good"/"CrateA_BaseColor.png")
    write_png(base/"exports_unreal_good"/"CrateA_Normal.png")
    write_png(base/"exports_unreal_good"/"CrateA_ORM.png")

    write_png(base/"exports_unity_missing"/"CrateB_BaseColor.png")
    write_png(base/"exports_unity_missing"/"CrateB_Normal.png")
    write_png(base/"exports_unity_missing"/"CrateB_Roughness.png")

    # naming issues (won't parse)
    write_png(base/"exports_naming_issues"/"CrateC.png")
    write_png(base/"exports_naming_issues"/"CrateC_Specular.png")

if __name__ == "__main__":
    main()
