# El Euro Claro · eleuroclaro.es

Web estática del canal El Euro Claro. Se publica con GitHub Pages desde la rama `main`.

- Últimos vídeos: `videos.js` (miniaturas solo desde `img/`, nunca URLs de otras webs)
- Enlace de alta a la newsletter: `NEWSLETTER_URL` en `site.js`
- Imagen para compartir en redes (1200×630): `img/og-eleuroclaro.png`; icono de pantalla de inicio: `apple-touch-icon.png`
- `404.html` usa rutas absolutas (`/style.css`) porque GitHub Pages la sirve en cualquier ruta que no exista
- `libros/index.html` (eleuroclaro.es/libros/): lista de libros; también usa rutas absolutas. Aún sin enlaces de compra: si se añaden enlaces de Amazon Afiliados, poner encima de la lista el aviso obligatorio de Amazon y quitar la frase «Sin enlaces de compra por ahora»
- Páginas de datos `euribor/index.html` y `alquiler-irav/index.html` (rutas absolutas): se actualizan cada mes con el dato oficial; la cifra también sale en la sección «Datos del mes» de `index.html` y la fecha en `sitemap.xml`. Textos de origen en canal-economia/web-textos/
- Sección «Kit» de `index.html` (`#kit`): el kit se vende en Gumroad (https://eleuroclaro.gumroad.com/l/kit; 15,70 € + IVA = 19 € en España). La oferta CLARO5 lleva `data-hasta` y `site.js` la muestra solo hasta esa fecha; para una oferta nueva, cambia el texto y la fecha. Si cambia el precio, cambia también la frase del precio
- `regalo/como-leer-tu-nomina.pdf`: regalo de bienvenida de la newsletter (lo hace el hilo del plan; el enlace va en el correo de bienvenida de Substack). No se enlaza desde la web y robots.txt lo excluye de buscadores
- Si añades una página, añádela también a `sitemap.xml`
- La web no usa cookies, analítica ni scripts de terceros; si eso cambia, hay que actualizar `cookies.html` y `privacidad.html`
