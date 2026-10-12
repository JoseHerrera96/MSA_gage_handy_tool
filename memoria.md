# Memoria del proyecto

## Corrección de imports al ejecutar desde otro dispositivo (2026-10-12)

- `MSA_app.py` importa la app desde `src/app`; un checkout sin instalación editable no podía resolver `app`.
- El launcher ahora agrega el directorio `src` del checkout a `sys.path`, calculado a partir de la ruta del propio archivo.
- README actualizado: `streamlit run MSA_app.py` puede ejecutarse desde el repositorio sin una instalación editable, siempre que las dependencias estén instaladas.
