# The landing page: static files served by nginx. Coolify builds it from this directory.
FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html icon.svg icon-*.png /usr/share/nginx/html/
