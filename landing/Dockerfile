# The landing page: static files served by nginx.
FROM nginx:1.29-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html icon.svg wordmark.svg icon-*.png /usr/share/nginx/html/
COPY fonts/ /usr/share/nginx/html/fonts/
