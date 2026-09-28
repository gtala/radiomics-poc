# Plan: modelo de nódulo pulmonar benigno / maligno

Guía de trabajo para pasar de la extracción de características (versión demo) a un modelo que estime la probabilidad de malignidad de un nódulo en una CT nueva.

Todo se desarrolla con datos públicos mientras se definen los criterios con el Dr. Plaza. Cuando haya datos o criterios propios, se reemplaza la fuente sin cambiar el circuito.

## Ambientes

| Ambiente | Rama | Uso |
|---|---|---|
| Demo | `main` (etiqueta `v0.1-demo`) | Versión que se muestra: solo extracción PyRadiomics. Solo correcciones. |
| Desarrollo | `dev` | Todo lo de este plan. Se pasa a `main` cuando esté probado. |

## Circuito

```
LIDC-IDRI (DICOM) ──► máscaras + etiquetas (pylidc) ──► PyRadiomics en lote ──► features.parquet
                                                                                     │
app: CT nueva + máscara ──► features ──► modelo.joblib ──► probabilidad  ◄── train.py (local)
```

- Imágenes: solo en local (`data/`, ignorado por Git).
- Features, modelo y reportes: archivos chicos, versionados en `dev`.
- Base de datos: no hace falta en esta etapa (ver Etapa 7).

## Etapa 1 — Datos

- [x] Dataset: **LIDC-IDRI** en [TCIA](https://www.cancerimagingarchive.net/collection/lidc-idri/). ~1.000 CT de tórax, nódulos segmentados por hasta 4 radiólogos, puntaje de malignidad 1–5. Licencia CC BY 3.0.
- [x] Descargar un subconjunto de **100–150 pacientes** con `tcia_utils` → `scripts/download_lidc.py` (paralelo, con reintentos). **114 pacientes** descargados (6 fallaron por cortes del servidor y se dejaron afuera).
- [x] Instalar y configurar `pylidc` → `scripts/lidc_compat.py` resuelve incompatibilidades con Python/NumPy actuales.
- [x] Verificar → `scripts/lidc_catalog.py`: 817 nódulos elegibles en todo LIDC-IDRI (494 benignos, 323 malignos).

## Etapa 2 — Criterios (provisorios, a validar con Plaza)

- **Etiqueta:** mediana del puntaje de malignidad de los radiólogos.
  - 4–5 → **maligno** · 1–2 → **benigno** · 3 → **excluido** (indeterminado).
- **Nódulos incluidos:** diámetro ≥ 3 mm y marcado por al menos 2 radiólogos.
- **Máscara:** consenso al 50 % entre radiólogos.
- **Serie:** espesor de corte ≤ 2,5 mm.
- **Limitación a declarar:** el puntaje es opinión radiológica, no biopsia. En datos propios, la referencia ideal es anatomía patológica o seguimiento.

## Etapa 3 — Extracción en lote

- [x] `scripts/extract_lidc.py`: por cada nódulo, genera volumen + máscara de consenso y corre PyRadiomics con la misma configuración que la app.
- [x] Salida: `outputs/features.parquet` → **194 nódulos** (119 benignos, 75 malignos), 1.218 features, sin errores.
- [x] Versiones de PyRadiomics y scikit-learn guardadas dentro del modelo.

## Etapa 4 — Entrenamiento y validación

- [x] `scripts/train.py`.
- [x] Separación **por paciente**: validación cruzada anidada 5×5 agrupada por paciente.
- [x] Selección de features: correlación |r| > 0,9 + LASSO → 45 features en el modelo final.
- [x] Modelos: regresión logística (elegida por interpretable) y random forest; empatan.
- [x] Métricas: AUC 0,96, sensibilidad 0,96, especificidad 0,94 · solo diámetro: AUC 0,94, sensibilidad 0,80.
- [x] Salida: `models/modelo_nodulo.joblib` + `reports/validacion.md` con gráficos.

## Etapa 5 — Probabilidad en la app

- [ ] Sección nueva **“Probabilidad estimada”** (solo en `dev`).
- [ ] Flujo: CT + máscara → features → modelo → probabilidad de malignidad.
- [ ] Mostrar las features que más influyeron (coeficientes o SHAP).
- [ ] Probabilidad calibrada y disclaimer: estimación académica, no diagnóstico.
- [ ] Opcional: que la interpretación asistida (LLM) explique el resultado del modelo.

## Etapa 6 — Segmentación automática

Hoy la máscara se hace a mano en 3D Slicer. Opciones a evaluar:

- **Semiautomática (primer paso):** el usuario marca un punto o caja sobre el nódulo y un algoritmo completa la máscara (crecimiento de regiones o modelos tipo SAM médico).
- **Automática:** modelos preentrenados de detección/segmentación de nódulos (por ejemplo el modelo de detección de nódulos de [MONAI Model Zoo](https://monai.io/model-zoo.html), o nnU-Net entrenado con LIDC / MSD Task06).
- Considerar: requiere más cómputo (idealmente GPU) y puede no entrar en el plan gratis de Streamlit Cloud → posible servicio aparte.

## Etapa 7 — Extras

- [ ] **Subir ZIP DICOM** directo a la app, con conversión automática a NIfTI y selección de serie.
- [ ] **Versión Colab** del circuito completo para que Plaza pueda usarlo sin instalar nada.
- [ ] **Modo RM** (T1, T2, difusión) con ventanas y configuración PyRadiomics propias.
- [ ] **Base de datos** (cuando la app guarde historial o feedback): Postgres en Supabase o Neon (plan gratis). Las imágenes nunca van en la base.

## Etapa 8 — Modelo híbrido (inspirado en productos como [Optellum](https://optellum.com/ai-technology))

El estado del arte combina deep learning + radiómica + datos clínicos. Pasos posibles, de más fácil a más difícil:

- [ ] **Datos clínicos:** edad, tabaquismo, antecedentes oncológicos (como el modelo de Brock). LIDC-IDRI casi no los trae → aplica con datos propios.
- [ ] **Features de deep learning preentrenado:** sumar embeddings de un modelo ya entrenado, por ejemplo el *Foundation Model for Cancer Imaging Biomarkers* (FMCIB, Nature Machine Intelligence 2024), preentrenado con más de 11.000 lesiones de CT. Funciona con pocos casos.
- [ ] **Segmentación con redes convolucionales** (ver Etapa 6).
- [ ] **Presentación al médico:** puntaje de riesgo en escala, integrado al flujo del nódulo, en lugar de una probabilidad cruda.
- No entrenar una red convolucional propia desde cero mientras haya pocos cientos de casos.

## Reglas

- No usar datos de pacientes reales sin autorización institucional y anonimización.
- Uso académico: no es una herramienta diagnóstica.
- Registrar versiones de datos, configuración y modelo en cada entrenamiento.
