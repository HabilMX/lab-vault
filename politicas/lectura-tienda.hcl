# La app de la tienda puede LEER sus secretos. Nada más.
path "secret/data/tienda/*" {
  capabilities = ["read"]
}
