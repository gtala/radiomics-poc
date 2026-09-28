# Visión del proyecto — Dr. Agustín Plaza

Resumen de la idea planteada por el Dr. Agustín Plaza (especialista en diagnóstico por imágenes), a partir de su audio del 22/09/2026.

## Qué es la radiómica, según su planteo

- Mide parámetros cuantitativos dentro de una lesión (la ROI): en tomografía, densidad en unidades Hounsfield (HU); en resonancia, señal T1, T2 y difusión.
- Detecta diferencias que el ojo no ve: valores medios, mínimos, variaciones finas de densidad o de restricción en difusión.
- Con muchos casos medidos se entrena un programa; después se sube una imagen nueva y el programa sugiere qué tipo de lesión podría ser.

## Antecedentes en su institución

- **Próstata:** modelo ya desarrollado, en etapa de validación.
- **Cáncer de cuello de útero:** modelo desarrollado.

## Trabajo actual

- **Nódulos pulmonares:** estimar si un nódulo es **probablemente benigno o probablemente maligno**.
- Parte de un cuaderno de Google Colab con datos en Google Drive, que recibió y está aprendiendo a usar.

## Hacia dónde quiere llegar

1. Usar la **misma base** (cuaderno / programa) para distintos temas, agregando la información de cada estudio.
2. **Cardiología:** vinculado a su trabajo sobre score de calcio coronario; aplicar la metodología a trombos y a la densidad real de las arterias coronarias.
3. Abrirlo a otros temas según el interés de cada colega. Considera que en tumores la aplicación es más sencilla.

## Qué aporta el proyecto técnico

- Cuaderno migrado a entorno local, versionado en Git y sincronizable con Colab.
- App web que carga volumen + máscara, visualiza cortes, extrae características con PyRadiomics, exporta CSV y genera una interpretación orientativa.
- Próximo paso propuesto: modelo **benigno / maligno para nódulo pulmonar**, entrenado primero con un dataset público (LIDC-IDRI) y luego, con autorización, con casos propios.

## Consideraciones

- El score de calcio (Agatston) es un cálculo estándar y no radiómica en sentido estricto; la radiómica cardiovascular actual estudia placa coronaria y grasa pericoronaria. Conviene tratarlo como segunda etapa.
- Para resonancia (T1, T2, difusión) la app necesita un modo específico: hoy está ajustada a tomografía.
- Uso académico: no es una herramienta diagnóstica.

## Preguntas abiertas para Agustín

1. En nódulos, ¿cómo se define benigno o maligno? (biopsia, seguimiento, criterio radiológico)
2. ¿Hay casos propios ya segmentados, o hay que segmentarlos? ¿Quién segmenta?
3. ¿Quién desarrolló los modelos de próstata y cuello uterino? ¿Podemos conocer su metodología?
4. ¿El trabajo pasa por comité de ética? ¿Quién autoriza el uso de estudios del hospital?
5. ¿Cuándo y en qué formato hay que presentar el trabajo? (póster, paper, demo)
