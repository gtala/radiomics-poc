# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: Python 3
#     name: python3
# ---

# %% [markdown] id="2isW6hz4XQEC"
# # Ejemplo de Extracción de Características Radiómicas mediante PyRadiomics
# PyRadiomics document: https://pyradiomics.readthedocs.io/en/latest/

# %% id="ZymtfVSBsucD"

# %% [markdown] id="rSo9nV-_QZX-"
# ## Instalación de PyRadiomics

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 48266, "status": "ok", "timestamp": 1788461827084, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="WP5E_44UXT4W" outputId="a02e5bb7-9969-41e9-adf1-342cb314322b"
# Entorno local: instalar dependencias con `pip install -r requirements.txt` en `.venv`.
# En Colab, descomentar la línea siguiente:
# En Colab: pip install git+https://github.com/AIM-Harvard/pyradiomics.git


# %% [markdown] id="1dxi_QGPU_tS"
#
#
# ---
#
#

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 21416, "status": "ok", "timestamp": 1788461848503, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="yZrKe2c8lowX" outputId="c23b1403-9485-4cbf-dca9-70eb10726b9c"
import os
from pathlib import Path


def _find_project_root() -> Path:
    if env := os.environ.get("RADIOMICA_PROJECT_ROOT"):
        return Path(env).expanduser().resolve()
    cwd = Path.cwd().resolve()
    for base in (cwd, *cwd.parents):
        if (base / "data").is_dir() and (base / "requirements.txt").exists():
            return base
    return cwd


# Datos locales: colocar archivos en ./data/ (ver README.md).
PROJECT_ROOT = _find_project_root()
DATA_DIR = Path(
    os.environ.get("RADIOMICA_DATA_DIR", PROJECT_ROOT / "data")
).expanduser().resolve()
print(f"Raíz del proyecto: {PROJECT_ROOT}")
print(f"Directorio de datos: {DATA_DIR}")


# %% [markdown] id="Q3ijYc1NQeZ4"
# ## Importación de Librerías

# %% executionInfo={"elapsed": 321, "status": "ok", "timestamp": 1788461848822, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="BA4rPifpUFwM"

import SimpleITK as sitk
import matplotlib.pyplot as plt
import numpy as np
from radiomics import featureextractor
import PIL

# %% [markdown] id="PI7nClcoU-FS"
#
#
# ---
#
#

# %% executionInfo={"elapsed": 1, "status": "ok", "timestamp": 1788461848824, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="RBF60FY-qEQj"
TC = str(DATA_DIR / "lung_001.nii.gz")
TC


# %% executionInfo={"elapsed": 36, "status": "ok", "timestamp": 1788461848862, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="XnIgay-IYooX"
Label = str(DATA_DIR / "lung_001_label.nii.gz")
Label


# %% [markdown] id="1qy7me68URTz"
# ## Uso de un Caso de Segmentación de Nódulo Pulmonar del dataset Medical Segmentation Decathlon
# http://medicaldecathlon.com/
#
# Los archivos NifTI con las imágenes y segmentaciones se cargan a través de SimpleITK.

# %% executionInfo={"elapsed": 12129, "status": "ok", "timestamp": 1788461860990, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="20KgmDy1UU0S"
image = sitk.ReadImage(TC)
segmentation = sitk.ReadImage(Label)

# %% executionInfo={"elapsed": 3, "status": "ok", "timestamp": 1788461860994, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="ff3GVgfjnTNn"

# %% [markdown] id="zKJZWKy-Uya6"
# ---
#
#
#

# %% colab={"base_uri": "https://localhost:8080/", "height": 187} executionInfo={"elapsed": 53, "status": "ok", "timestamp": 1788461861048, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="wvU3bhYtr1AL" outputId="2b0b6886-ef2d-43fb-95c9-4ca72d3991b8"
type (image)

# %% executionInfo={"elapsed": 2, "status": "ok", "timestamp": 1788461861066, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="ZopxRHaPeI8w"
texto = "esto es un texto"

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 5, "status": "ok", "timestamp": 1788461861075, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="BYfadH8cedH5" outputId="1099e90d-8c00-4951-f0fd-e9dc089644c1"
type (texto)

# %% executionInfo={"elapsed": 67, "status": "ok", "timestamp": 1788461861143, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="sDDcLCsLe2qi"
sikt = ["budin", "auto, casa"]

# %% colab={"base_uri": "https://localhost:8080/", "height": 35} executionInfo={"elapsed": 11, "status": "ok", "timestamp": 1788461861144, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="eA8N-AOCe-5T" outputId="27210d7e-3f47-4a20-9f28-7beb6d69eff6"
sikt[1]

# %% executionInfo={"elapsed": 7, "status": "ok", "timestamp": 1788461861145, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="aUNyQcDigU3B"
N= [0, sikt, 13,13,1414]

# %% colab={"base_uri": "https://localhost:8080/", "height": 187} executionInfo={"elapsed": 37, "status": "ok", "timestamp": 1788461861178, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="09EjLy3ppwJX" outputId="5d7826bf-e327-4175-bf40-0826a3b92d48"
type(image)

# %% [markdown] id="92njGjpXPmDw"
# ## Archivo de Configuración de TC de PyRadiomics
# https://github.com/AIM-Harvard/pyradiomics/tree/master/examples/exampleSettings

# %% executionInfo={"elapsed": 47, "status": "ok", "timestamp": 1788461861225, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="WsKYCJbYbW5V"
TC_config = str(DATA_DIR / "CT_config.yaml")
# Alternativa: config de ejemplo incluida en el repo
# TC_config = str(PROJECT_ROOT / "config" / "exampleCT.yaml")
TC_config


# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 10, "status": "ok", "timestamp": 1788461861226, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="mWO3hcsstb3X" outputId="e16ba7d5-27f2-4045-a223-ddf59dd00668"
type(TC_config)

# %% [markdown] id="lZ5oxVxfVBs6"
#
#
# ---
#
#

# %% [markdown] id="V0VlC8k8uhSt"
# ## Visión de un Corte

# %% colab={"base_uri": "https://localhost:8080/", "height": 418} executionInfo={"elapsed": 1295, "status": "ok", "timestamp": 1788461862519, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="xb4OEO2eugaR" outputId="416d44d3-7a2f-4189-ed32-0a0a175e9a64"
z = 240


hu_l = -1000
hu_h = -100

array_img = sitk.GetArrayFromImage(image)
array_seg = sitk.GetArrayFromImage(segmentation)

I = np.flipud(array_img[z, :, :])
S = np.flipud(array_seg[z, :, :])

plt.figure(figsize=(10, 10))
plt.subplot(1, 2, 1)
plt.imshow(I, cmap='gray', vmin=hu_l, vmax=hu_h)
plt.subplot(1, 2, 2)
plt.imshow(S)
plt.show()

# %% executionInfo={"elapsed": 62, "status": "ok", "timestamp": 1788461862580, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="5AMtp5cwvWvq"
arrayImg = sitk.GetArrayFromImage(image)


# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 68, "status": "ok", "timestamp": 1788461862666, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="XInaEjppvolL" outputId="ed6cb6df-ef9f-4d05-879c-d917a043eceb"
arrayImg.min

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 85, "status": "ok", "timestamp": 1788461862752, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="jfB2gOekwauE" outputId="d4be63ce-ca7f-46bb-f85d-abed70c57225"
type(arrayImg)

# %% [markdown] id="YpoJ45fQwZ8N"
#

# %% executionInfo={"elapsed": 2, "status": "ok", "timestamp": 1788461862755, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="_HZCSlwEv0bq"
corte237 = arrayImg[237,:,:]

# %% colab={"base_uri": "https://localhost:8080/", "height": 552} executionInfo={"elapsed": 124, "status": "ok", "timestamp": 1788461862882, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="xUYQoQEIck6G" outputId="c4e70b6a-3d29-4b34-c9e1-3abcb3e9c3bf"
corte237.astype(np.uint8)

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 8, "status": "ok", "timestamp": 1788461862892, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="0KsiWLoJdEYk" outputId="3335d528-c60e-4ef2-f0fd-d561305d3a5e"
2**8

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 10, "status": "ok", "timestamp": 1788461862903, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="-2elgvVU9xTV" outputId="a05cc8ce-059f-4741-ec63-03b8c0489857"
print(corte237.astype(np.uint8).mean())

# %% colab={"base_uri": "https://localhost:8080/", "height": 529} executionInfo={"elapsed": 45, "status": "ok", "timestamp": 1788461862948, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="25c79bf5" outputId="2cf75791-b576-47c0-da98-aa241a2e1e92"
import numpy as np
import PIL.Image
from IPython.display import display

# Get min and max values for scaling
min_val = corte237.min()
max_val = corte237.max()

# Normalize to 0-255 range
scaled_corte237 = 255 * (corte237 - min_val) / (max_val - min_val)

# Convert to uint8
grayscale_image_uint8 = scaled_corte237.astype(np.uint8)

# Create a PIL Image from the uint8 array
imagenVisible_scaled = PIL.Image.fromarray(grayscale_image_uint8)

# Flip the image vertically
imagenVisible_scaled = imagenVisible_scaled.transpose(PIL.Image.FLIP_TOP_BOTTOM)

# Display the image
display(imagenVisible_scaled)

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 5, "status": "ok", "timestamp": 1788461862955, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="PdSWu8MTyyOS" outputId="9a8a9fe5-0a2b-4aef-dce7-a1bb4db74f64"
corte237

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 8, "status": "ok", "timestamp": 1788461862966, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="uENLARtF_xhW" outputId="a6b22d86-a5c0-4992-8966-73977cc3a9f2"
corte237.max()

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 8, "status": "ok", "timestamp": 1788461862976, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="BponRwCddiyp" outputId="6e276c43-add9-4ffc-b706-9e1112348335"
grayscale_image_uint8.shape

# %% colab={"base_uri": "https://localhost:8080/", "height": 552} executionInfo={"elapsed": 27, "status": "ok", "timestamp": 1788461863004, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="M_hIIrZar4Uj" outputId="98d60402-d7eb-4b2f-94b0-9ba1de43ab28"
grayscale_image_uint8

# %% executionInfo={"elapsed": 3, "status": "ok", "timestamp": 1788461863010, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="v6PyDPBnr3s6"
corte_nodulo=grayscale_image_uint8.copy()

# %% executionInfo={"elapsed": 26, "status": "ok", "timestamp": 1788461863037, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="NJebmrTIsII5"
corte_nodulo=np.flipud(corte_nodulo)

# %% colab={"base_uri": "https://localhost:8080/", "height": 552} executionInfo={"elapsed": 26, "status": "ok", "timestamp": 1788461863061, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="DkRZwMICsIF5" outputId="5457099c-1952-4baa-f9d8-0e1f5f0268f6"
corte_nodulo

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 16, "status": "ok", "timestamp": 1788461863078, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="_JTSeiZStC1S" outputId="84c43c03-377d-4adc-fd9e-bdd728aedfea"
corte_nodulo.shape

# %% executionInfo={"elapsed": 2, "status": "ok", "timestamp": 1788461863081, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="Pbep94UrtUHT"
nodulo=corte_nodulo[220:270,100:150]

# %% colab={"base_uri": "https://localhost:8080/", "height": 90} executionInfo={"elapsed": 2, "status": "ok", "timestamp": 1788461863084, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="LVX9H8TfsIAZ" outputId="f29f1e29-06e4-4c85-aec5-fa28cabb714d"
nodulo

# %% executionInfo={"elapsed": 1, "status": "ok", "timestamp": 1788461863086, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="KRAopbBSvsL7"
nodulo_umbral=nodulo.copy()

# %% executionInfo={"elapsed": 22, "status": "ok", "timestamp": 1788461863108, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="POmmIbhfsHvB"
nodulo_umbral[nodulo_umbral<60]=0

# %% colab={"base_uri": "https://localhost:8080/", "height": 90} executionInfo={"elapsed": 33, "status": "ok", "timestamp": 1788461863142, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="5bQWY3-0sHkB" outputId="4e112ade-ff42-4527-eac4-a82478182bc5"
nodulo_umbral

# %% executionInfo={"elapsed": 1, "status": "ok", "timestamp": 1788461863144, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="a6XMGaJcx1HL"
nodulo_umbral[nodulo_umbral>70]=0

# %% colab={"base_uri": "https://localhost:8080/", "height": 90} executionInfo={"elapsed": 36, "status": "ok", "timestamp": 1788461863181, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="S119W0Q_yHQD" outputId="b2685951-a1e8-4d36-ca7d-76954a6aa606"
nodulo_umbral

# %% executionInfo={"elapsed": 14, "status": "ok", "timestamp": 1788461863226, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="gax02KSTx1zL"
#trabajar umbral con UH, de corte237

# %% executionInfo={"elapsed": 1, "status": "ok", "timestamp": 1788461863228, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="Eph96aTKALr8"
nodulo_umbralUH= corte237.copy()

# %% executionInfo={"elapsed": 28, "status": "ok", "timestamp": 1788461863298, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="mdkAw77TAmL4"
nodulo_umbralUH[nodulo_umbralUH>40]=0

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 9, "status": "ok", "timestamp": 1788461863309, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="qc2tbBV4AmJY" outputId="5736fbb9-ef86-4bda-aa19-894081b5ae81"
nodulo_umbralUH

# %% executionInfo={"elapsed": 2, "status": "ok", "timestamp": 1788461863312, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="pBcXinruelvD"
img_3c = np.zeros((512,512,3),dtype=np.uint8)

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 13, "status": "ok", "timestamp": 1788461863326, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="tkMta9dVewaR" outputId="b304f87f-c85a-4b14-e58a-3e94d13a8a3d"
img_3c.shape

# %% executionInfo={"elapsed": 7, "status": "ok", "timestamp": 1788461863334, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="zAAyTu48fPuf"
img_3c = np.zeros((512,512,3),dtype=np.uint8)
img_3c[:,:,0] = grayscale_image_uint8
img_3c[:,:,1] = grayscale_image_uint8
img_3c[:,:,2] = grayscale_image_uint8


# %% colab={"base_uri": "https://localhost:8080/", "height": 552} executionInfo={"elapsed": 78, "status": "ok", "timestamp": 1788461863413, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="ETuxVPfurJ5P" outputId="c179dcea-99e6-47c1-a0b8-cc4d244d0456"
img_3c[:,:,1]

# %% colab={"base_uri": "https://localhost:8080/", "height": 552} executionInfo={"elapsed": 22, "status": "ok", "timestamp": 1788461863438, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="NdljRz-osJHa" outputId="9f813310-3ac1-4c79-b617-ca3c2205e5a7"
np.flipud(img_3c)

# %% colab={"base_uri": "https://localhost:8080/", "height": 552} executionInfo={"elapsed": 60, "status": "ok", "timestamp": 1788461863500, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="V00E8EoQf1J6" outputId="d2b76f3d-f9ac-4c69-f7ed-ddc490890e72"
img_3c

# %% [markdown] id="s1Z72zZ2s0uB"
# segmentar con un cuadrado o box el nódulo y extraer solo los pixeles del nodulo a partir del umbral.-

# %% executionInfo={"elapsed": 3, "status": "ok", "timestamp": 1788461863505, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="xDFqG2OSgEXn"
img_3c[200:300,200:300,1] = grayscale_image_uint8[200:300,200:300]

# %% colab={"base_uri": "https://localhost:8080/", "height": 552} executionInfo={"elapsed": 69, "status": "ok", "timestamp": 1788461863573, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="YZRE_9z0gIAf" outputId="dc402168-8f1a-4418-ae81-c9701191a5b0"
img_3c

# %% executionInfo={"elapsed": 5, "status": "ok", "timestamp": 1788461863574, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="H7wd9k9FgUm2"
img_3c[200:300,200:300,2] = grayscale_image_uint8[200:300,200:300]

# %% executionInfo={"elapsed": 5, "status": "ok", "timestamp": 1788461863576, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="978XJwMUlbWT"
img_3c[200:300,200:300,1] = 0
img_3c[200:300,200:300,0] = 0

# %% executionInfo={"elapsed": 3, "status": "ok", "timestamp": 1788461863580, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="HXfPYc12pmXb"
img_3c = np.zeros((512,512,3),dtype=np.uint8)
img_3c[:,:,0] = grayscale_image_uint8
img_3c[:,:,1] = grayscale_image_uint8
img_3c[:,:,2] = grayscale_image_uint8

# %% executionInfo={"elapsed": 25, "status": "ok", "timestamp": 1788461863606, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="gJXt7MOPoSMi"
array_seg = sitk.GetArrayFromImage(segmentation)

# %% colab={"base_uri": "https://localhost:8080/"} executionInfo={"elapsed": 12, "status": "ok", "timestamp": 1788461863620, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="QQrAXiDUqS1Z" outputId="341c7127-4a86-482e-ce2c-6d1fb9487577"
array_seg.shape

# %% executionInfo={"elapsed": 5, "status": "ok", "timestamp": 1788461863621, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="QZDDm3qcpHCd"
corte_nodulo = array_seg[237,:,:]

# %% executionInfo={"elapsed": 5, "status": "ok", "timestamp": 1788461863623, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="9EBu340Lq1gn"
corte_nodulo = corte_nodulo*255

# %% executionInfo={"elapsed": 4, "status": "ok", "timestamp": 1788461863623, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="WiMmfN7LoroI"
img_3c[:,:,2] = corte_nodulo

# %% colab={"base_uri": "https://localhost:8080/", "height": 552} executionInfo={"elapsed": 121, "status": "ok", "timestamp": 1788461863742, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="miR8j7VTgZCd" outputId="37d3c5a7-bccd-45dc-8aac-ff3099b03d61"
np.flipud(img_3c)

# %% colab={"base_uri": "https://localhost:8080/", "height": 106} executionInfo={"elapsed": 3, "status": "error", "timestamp": 1788461863772, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="QQ0BYLirgQLZ" outputId="7b154907-c8d4-40dd-d3db-2dd53185d0d1"
# Nota: cómo hacer para que el resto de la TC se vea en escala de grises y no amarillo


# %% executionInfo={"elapsed": 85277, "status": "aborted", "timestamp": 1788461863740, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="lxK-Jt5wbpjn"
corte237.mean()

# %% executionInfo={"elapsed": 7, "status": "aborted", "timestamp": 1788461863898, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="vJtNVGkF44ow"
512*512

# %% executionInfo={"elapsed": 8, "status": "aborted", "timestamp": 1788461863900, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="J-_jj5ut6Ymk"
imagenVisible = PIL.Image.fromarray(arrayImg[237,:,:])

# %% executionInfo={"elapsed": 7, "status": "aborted", "timestamp": 1788461863901, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="JvAVk31dqjBN"
display(imagenVisible)

# %% [markdown] id="J2AHguyiREd9"
# ## Extracción de Características Radiómicas
# Utilizamos el archivo de configuración para el setup del extractor.
#
# Se provee la imagen y la etiqueta (ROI) mediante formato SimpleITK.
#
# Etiquetas --> 0 Fondo.
#               1 Nódulo.

# %% executionInfo={"elapsed": 8, "status": "aborted", "timestamp": 1788461863903, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="bi00TYJVamcx"
extractor = featureextractor.RadiomicsFeatureExtractor(TC_config, preCrop=True)

# %% [markdown] id="5m_Dfx-SXO7q"
# ## Configuración del Extractor de Características Radiómicas
# Documentación: https://pyradiomics.readthedocs.io/en/latest/customization.html#radiomics-customization-label

# %% executionInfo={"elapsed": 8, "status": "aborted", "timestamp": 1788461863904, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="n5qkomqy7Yin"
extractor.settings

# %% [markdown] id="fcVzGEGPX1tX"
# Se puede modificar la configuración, por ejemplo en el 'binWith'
#
# extractor.settings['binWidth'] = 25

# %% [markdown] id="yv9_-PtkXhzf"
#
#
# ---
#
#

# %% executionInfo={"elapsed": 9, "status": "aborted", "timestamp": 1788461863906, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="kbDOmYzUQbk9"
caracteristicas_nodulo = extractor.execute(image, segmentation, label=1)

# %% executionInfo={"elapsed": 85413, "status": "aborted", "timestamp": 1788461863908, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="oe95j1VkQq3m"
caracteristicas_nodulo

# %% [markdown] id="V-fU8ZQSaKut"
#
#
# ---
#
#

# %% [markdown] id="yAxrX3EgaLrE"
# ### Cantidad de Características del Nódulo

# %% executionInfo={"elapsed": 85411, "status": "aborted", "timestamp": 1788461863911, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="YrdBnJkdZ4xU"
len(caracteristicas_nodulo)

# %% [markdown] id="65mmRnCyYZOO"
#
#
# ---
#
#

# %% [markdown] id="fq0A2xGOlwbM"
# ### Lectura de Características del Nódulo

# %% executionInfo={"elapsed": 85409, "status": "aborted", "timestamp": 1788461863914, "user": {"displayName": "Karen Andreina", "userId": "15838606844898234510"}, "user_tz": 180} id="Xa1PqqJoiFy7"
caracteristica = 'original_shape_MeshVolume'
#caracteristica = 'original_firstorder_Minimum'

print(caracteristicas_nodulo[caracteristica])

# %% [markdown] id="2ulAQhNoYdc2"
#
#
# ---
#
#
