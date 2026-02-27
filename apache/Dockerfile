FROM httpd:2.4-alpine

# Enable required modules
RUN sed -i \
    -e 's/#LoadModule proxy_module/LoadModule proxy_module/' \
    -e 's/#LoadModule proxy_http_module/LoadModule proxy_http_module/' \
    -e 's/#LoadModule proxy_wstunnel_module/LoadModule proxy_wstunnel_module/' \
    -e 's/#LoadModule rewrite_module/LoadModule rewrite_module/' \
    -e 's/#LoadModule headers_module/LoadModule headers_module/' \
    -e 's/#LoadModule ssl_module/LoadModule ssl_module/' \
    /usr/local/apache2/conf/httpd.conf

# Include our custom config
RUN echo "Include conf/extra/gartenapp.conf" >> /usr/local/apache2/conf/httpd.conf

COPY gartenapp.conf /usr/local/apache2/conf/extra/gartenapp.conf
