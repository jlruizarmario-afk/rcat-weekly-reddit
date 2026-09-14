# rcat-weekly-reddit

Primera versión: Reddit → Python → `weekly_comments.json`.
No utiliza Claude ni GitHub Actions.

## Requisitos

- Python 3.9 o posterior (recomendado: 3.11 o posterior).
- Acceso aprobado a la API de Reddit y credenciales de aplicación
  (`client_id`, `client_secret`). Reddit exige aprobación explícita:
  [política oficial](https://support.reddithelp.com/hc/en-us/articles/42728983564564-Responsible-Builder-Policy).
  Si aún no tienes acceso, empieza por esa página; crear un repositorio GitHub
  no concede acceso a Reddit. No hacen falta claves de Claude.

## Prueba manual (macOS / Linux)

Abre una terminal dentro de la carpeta del repositorio con estos archivos:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Abre `.env` en tu editor y sustituye los tres valores de ejemplo por tus
credenciales y tu usuario real de Reddit. No publiques ese archivo ni pegues
el secreto en conversaciones. `.gitignore` ya lo excluye del repositorio.

Ejecuta:

```bash
python main.py
python -m json.tool weekly_comments.json
```

La descarga puede tardar varios minutos: se expanden todas las ramas accesibles,
incluidas las respuestas dentro de respuestas. PRAW gestiona los límites normales
de la API; los fallos que no recupera quedan señalados en el resultado.

Para una prueba inicial más pequeña o para conservar otra salida:

```bash
python main.py --days 1 --output prueba.json
```

No subas los JSON descargados al repositorio; el nombre de prueba personalizado
no está cubierto por la regla `weekly_comments*.json` de `.gitignore`.

## Qué comprueba y qué guarda

- Recorre las publicaciones recientes de r/RedCatHoldings directamente con la
  API de Reddit, sin Google. Selecciona títulos que contienen «Daily Discussion»,
  sin distinguir mayúsculas, publicados en las últimas 168 horas por defecto.
- El intervalo corresponde a la fecha del hilo, no a la fecha de cada comentario.
  Incluye todos los comentarios disponibles cuando se descarga cada hilo.
  No presupone que existan exactamente siete hilos.
- Usa `replace_more(limit=None, threshold=0)` para expandir las ramas:
  [documentación PRAW](https://praw.readthedocs.io/en/stable/code_overview/other/commentforest.html).
- Guarda título, texto y enlace de cada hilo; y texto, autor, fecha, puntuación,
  enlace e identificador de cada comentario. `parent_id` conserva la jerarquía:
  `t3_...` apunta al hilo y `t1_...` a otro comentario.
- No recupera textos borrados, retirados o inaccesibles. Conserva los marcadores
  `[deleted]` y `[removed]` que entregue Reddit y usa `null` para autores ausentes.
- `status: complete` significa que se alcanzó el inicio del intervalo y se
  expandieron sin errores todas las ramas que entregó la API. No garantiza
  acceso a contenido oculto ni una instantánea simultánea de todos los hilos.
- Si el listado se termina antes de llegar al inicio del intervalo, marca
  `partial`: Reddit limita el historial de sus listados. Consulta `discovery`.
  Si falla un hilo, conserva lo descargado y continúa con los demás.
- El contador de Reddit puede diferir de los comentarios recuperados por
  moderación, borrados o cambios durante la descarga. Se guardan ambos contadores.

Comprueba `status`, `discovery`, `threads` y `total_comments` en el JSON.
Si aparecen cero hilos, verifica las fechas y títulos en Reddit: cero no significa
necesariamente un error. La ejecución devuelve código 0 si terminó completa,
1 si falta configuración y 2 si la descarga quedó parcial.

Cada ejecución sustituye el archivo de salida, con guardados tras cada hilo.
Usa `--output otro_archivo.json` para conservar una ejecución anterior.

## Añadir a GitHub

Coloca `main.py`, `requirements.txt`, `.env.example`, `.gitignore` y este README
en la raíz de tu repositorio `rcat-weekly-reddit` y guarda los cambios. También
puedes crearlos desde GitHub con **Add file → Create new file**. La prueba se
ejecuta en tu ordenador: subir los archivos a GitHub no ejecuta el programa.

## Validación de esta entrega

Se han comprobado la sintaxis y el comportamiento con datos simulados (ventana
temporal, respuestas, duplicados y descarga parcial). Falta la prueba real con
credenciales aprobadas de Reddit; no se incluye un JSON ficticio de producción.
