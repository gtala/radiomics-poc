# Radiómica cuantitativa

Plataforma académica para análisis radiómico de estudios de tomografía computada (CT): visualización de volúmenes y regiones de interés (ROI), extracción de características con PyRadiomics e interpretación asistida orientativa (sin uso diagnóstico).

Incluye también el cuaderno de trabajo derivado del análisis original de referencia, con el mismo flujo de celdas para uso local o Colab.

## App web

```bash
cd radiomica-poc
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

Código principal: `app/streamlit_app.py`, `app/radiomics_service.py`, `app/viewer.py`, `app/interpret.py`.

### Interpretación asistida (opcional)

Configure `OPENAI_API_KEY` en un archivo `.env` local (ver `.env.example`) o en **Secrets** de Streamlit Community Cloud. La interpretación describe métricas cuantitativas; **no diagnostica**.

### Deploy (Streamlit Community Cloud)

1. Repositorio en GitHub (`gtala/radiomics-poc`).
2. https://share.streamlit.io → **New app** → branch `main`.
3. **Main file path:** `app/streamlit_app.py`
4. **Secrets** (Toml):

```toml
OPENAI_API_KEY = "sk-..."
OPENAI_MODEL = "gpt-4o-mini"
```

5. En la nube hay que **cargar** volumen + máscara (no se incluyen NIfTI de demostración).
6. No utilice estudios clínicos reales en instancias públicas.

## Archivos del cuaderno

| Archivo | Uso |
|---------|-----|
| `notebooks/original/Radiomica_Nodulo_Pulmonar.recibido_COLAB.ipynb` | Copia de referencia (Colab). |
| `notebooks/Radiomica_Nodulo_Pulmonar.ipynb` | Cuaderno de trabajo (rutas locales). |
| `notebooks/Radiomica_Nodulo_Pulmonar.py` | Mismo contenido en formato Jupytext `percent`. |

## Datos locales (opcional)

Coloque en `data/` (ignorado por Git):

- Volumen CT (`.nii` / `.nii.gz`)
- Máscara / segmentación de la ROI
- `CT_config.yaml` — configuración PyRadiomics

Plantilla de referencia: `config/exampleCT.yaml`.

```bash
export RADIOMICA_DATA_DIR="/ruta/absoluta/a/tus/datos"
```

## Entorno virtual

```bash
cd radiomica-poc
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements-local.txt
python -m ipykernel install --user --name=radiomica-poc --display-name="Python (radiomica-poc)"
```

En Streamlit Community Cloud se usa `requirements.txt` (pip).

## Ejecutar el cuaderno en Cursor

1. Extensión **Jupyter**.
2. Abrir `notebooks/Radiomica_Nodulo_Pulmonar.ipynb`.
3. Kernel **Python (radiomica-poc)**.
4. Ejecutar las celdas en orden.

## Sincronizar `.py` y `.ipynb` (Jupytext)

```bash
source .venv/bin/activate
jupytext --sync notebooks/Radiomica_Nodulo_Pulmonar.ipynb
```

Configuración: `.jupytext.toml`.

## Privacidad

El cuaderno de referencia puede incluir salidas con datos derivados de imagen. No suba esos archivos ni el contenido de `data/` a repositorios públicos. La copia de trabajo en el repo va **sin salidas** ejecutadas.

## Ciclo de trabajo recomendado

1. Editar `notebooks/Radiomica_Nodulo_Pulmonar.py` o la app en `app/`.
2. Sincronizar cuaderno si aplica → `jupytext --sync …`
3. Probar localmente.
4. Commit y push a `main` (Streamlit Cloud se actualiza solo).
