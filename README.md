# Radiómica — Nódulo pulmonar (POC local)

Proyecto local del cuaderno **Radiómica - Nódulo PulmonarAGUS**, con el mismo análisis y estructura de celdas que en Google Colab.

## Archivos del cuaderno

| Archivo | Uso |
|---------|-----|
| `notebooks/original/Radiomica_Nodulo_Pulmonar.recibido_COLAB.ipynb` | Copia del cuaderno recibido (referencia Colab). |
| `notebooks/Radiomica_Nodulo_Pulmonar.ipynb` | Cuaderno de trabajo (rutas locales). |
| `notebooks/Radiomica_Nodulo_Pulmonar.py` | Mismo contenido en formato Jupytext `percent` (edición en Cursor). |

## Datos necesarios

Colocá estos archivos en `data/` (no se suben a Git):

- `lung_001.nii.gz` — volumen CT (Medical Segmentation Decathlon, tarea pulmonar).
- `lung_001_label.nii.gz` — segmentación del nódulo.
- `CT_config.yaml` — configuración PyRadiomics usada en Colab.

En esta máquina **no están** esos tres archivos; solo hay `config/exampleCT.yaml` como plantilla de referencia PyRadiomics (no es necesariamente la misma config que en Colab).

Variable opcional:

```bash
export RADIOMICA_DATA_DIR="/ruta/absoluta/a/tus/datos"
```

## Entorno virtual

```bash
cd radiomica-poc
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
python -m ipykernel install --user --name=radiomica-poc --display-name="Python (radiomica-poc)"
```

## Ejecutar en Cursor

1. Instalá la extensión **Jupyter** (Microsoft) si no la tenés: buscá “Jupyter” en Extensiones.
2. Abrí `notebooks/Radiomica_Nodulo_Pulmonar.ipynb`.
3. Arriba a la derecha, elegí el kernel **Python (radiomica-poc)** (interpreter de `.venv`).
4. Ejecutá las celdas en orden.

La celda de instalación de Colab quedó comentada; las dependencias vienen de `requirements.txt`.

## Sincronizar `.py` y `.ipynb` (Jupytext)

Tras editar el script Python:

```bash
source .venv/bin/activate
jupytext --sync notebooks/Radiomica_Nodulo_Pulmonar.ipynb
```

- Editás `notebooks/Radiomica_Nodulo_Pulmonar.py` → el comando actualiza el `.ipynb`.
- Si editás solo el `.ipynb`, podés sincronizar hacia el `.py` con el mismo comando.

Configuración: `.jupytext.toml`.

## Privacidad

El cuaderno **recibido** incluye salidas con valores HU y matrices de píxeles de TC (datos clínicos derivados). No subas esos archivos ni datos en `data/` a repositorios públicos. La copia de trabajo en el repo va **sin salidas** ejecutadas.

## Publicar en GitHub (privado)

```bash
gh auth login
gh repo create radiomica-poc --private --source=. --remote=origin --push
```

Si el repo ya existe:

```bash
git remote add origin git@github.com:TU_USUARIO/radiomica-poc.git
git push -u origin main
```

## Ciclo de trabajo recomendado

1. **Editar** `notebooks/Radiomica_Nodulo_Pulmonar.py` en Cursor.
2. **Sincronizar** → `jupytext --sync notebooks/Radiomica_Nodulo_Pulmonar.ipynb`
3. **Probar** el `.ipynb` con kernel `Python (radiomica-poc)`.
4. **Commit** → `git add notebooks/Radiomica_Nodulo_Pulmonar.py notebooks/Radiomica_Nodulo_Pulmonar.ipynb && git commit -m "..."`
5. **Push** → `git push`
6. **Colab** → subir o abrir desde GitHub el `.ipynb` actualizado (datos en Drive o en `data/` según entorno).
