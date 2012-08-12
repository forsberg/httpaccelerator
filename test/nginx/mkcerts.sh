#!/bin/bash
# Shamelessly copied from http://blog.nategood.com/client-side-certificate-authentication-in-ngi

# Create the CA Key and Certificate for signing Client Certs
echo "** Creating CA key"
openssl genrsa -des3 -out ssl/ca.key 4096
echo "** Creating CA certificate"
openssl req -new -x509 -days 365 -key ssl/ca.key -out ssl/ca.crt

# Create the Server Key, CSR, and Certificate
echo "** Creating server key"
openssl genrsa -des3 -out ssl/server.key 1024
echo "** Creating server CSR"
openssl req -new -key ssl/server.key -out ssl/server.csr

# We're self signing our own server cert here.  This is a no-no in production.
echo "** Signing server certificate"
openssl x509 -req -days 365 -in ssl/server.csr -CA ssl/ca.crt -CAkey ssl/ca.key -set_serial 01 -out ssl/server.crt

# Create the Client Key and CSR
echo "** Creating client key"
openssl genrsa -des3 -out ssl/client.key 1024
echo "** Creating client CSR"
openssl req -new -key ssl/client.key -out ssl/client.csr

# Sign the client certificate with our CA cert.  Unlike signing our own server cert, this is what we want to do.
echo "** Signing client CSR"
openssl x509 -req -days 365 -in ssl/client.csr -CA ssl/ca.crt -CAkey ssl/ca.key -set_serial 01 -out ssl/client.crt