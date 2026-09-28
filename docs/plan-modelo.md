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

- [ ] Dataset: **LIDC-IDRI** en [TCIA](https://www.cancerimagingarchive.net/collection/lidc-idri/). ~1.000 CT de tórax, nódulos segmentados por hasta 4 radiólogos, puntaje de malignidad 1–5. Licencia CC BY 3.0.
- [ ] Descargar un subconjunto de **100–150 pacientes** (~10–20 GB; el total pesa ~124 GB) con [NBIA Data Retriever](https://wiki.cancerimagingarchive.net/display/NBIA/Downloading+TCIA+Images) o el paquete `tcia_utils`.
- [ ] Instalar y configurar `pylidc` (lee las anotaciones XML y arma las máscaras).
- [ ] Verificar: cantidad de pacientes, nódulos y distribución de puntajes.

## Etapa 2 — Criterios (provisorios, a validar con Plaza)

- **Etiqueta:** mediana del puntaje de malignidad de los radiólogos.
  - 4–5 → **maligno** · 1–2 → **benigno** · 3 → **excluido** (indeterminado).
- **Nódulos incluidos:** diámetro ≥ 3 mm y marcado por al menos 2 radiólogos.
- **Máscara:** consenso al 50 % entre radiólogos.
- **Serie:** espesor de corte ≤ 2,5 mm.
- **Limitación a declarar:** el puntaje es opinión radiológica, no biopsia. En datos propios, la referencia ideal es anatomía patológica o seguimiento.

## Etapa 3 — Extracción en lote

- [ ] `scripts/extract_lidc.py`: por cada nódulo, genera volumen + máscara y corre PyRadiomics (reutiliza `app/radiomics_service.py`).
- [ ] Salida: `outputs/features.parquet` (una fila por nódulo: id de paciente, id de nódulo, etiqueta, features).
- [ ] Guardar la configuración YAML y la versión de PyRadiomics usadas (reproducibilidad, IBSI).

## Etapa 4 — Entrenamiento y validación

- [ ] `scripts/train.py`.
- [ ] Separación **por paciente** (nunca el mismo paciente en entrenamiento y prueba).
- [ ] Selección de features: eliminar las muy correlacionadas (|r| > 0,9) y seleccionar con LASSO → objetivo 10–30 features.
- [ ] Modelos: regresión logística (interpretable) y random forest; comparar.
- [ ] Validación cruzada estratificada por paciente + conjunto de prueba reservado.
- [ ] Métricas: AUC, sensibilidad, especificidad, curva ROC, **calibración**.
- [ ] Salida: `models/modelo.joblib` + `reports/validacion.md` con gráficos.

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

## Reglas

- No usar datos de pacientes reales sin autorización institucional y anonimización.
- Uso académico: no es una herramienta diagnóstica.
- Registrar versiones de datos, configuración y modelo en cada entrenamiento.
