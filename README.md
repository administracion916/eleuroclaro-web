# El Euro Claro · eleuroclaro.es

Web estática del canal El Euro Claro. Se publica con GitHub Pages desde la rama `main`.

- Últimos vídeos: `videos.js` (miniaturas solo desde `img/`, nunca URLs de otras webs)
- Enlace de alta a la newsletter: `NEWSLETTER_URL` en `site.js`
- Imagen para compartir en redes (1200×630): `img/og-eleuroclaro.png`; icono de pantalla de inicio: `apple-touch-icon.png`
- `404.html` usa rutas absolutas (`/style.css`) porque GitHub Pages la sirve en cualquier ruta que no exista
- Si añades una página, añádela también a `sitemap.xml`
- La web no usa cookies, analítica ni scripts de terceros; si eso cambia, hay que actualizar `cookies.html` y `privacidad.html`
