# Peças a partir de fotos (T9)

`tools/garment_from_photos.py` transforma fotos de uma peça real em um GLB rigado com a textura projetada no UV do
template (`assets/garments/photo_<nome>.glb`, mais um `.meta.json`). O app a carrega junto com as outras.

```
python tools/garment_from_photos.py --sheet assets/photos/sesi/folha.jpg --name "Camiseta SESI"
python tools/garment_from_photos.py --front frente.jpg --back costas.jpg --name "Camiseta X"
python tools/garment_from_photos.py ... --debug-dir debug/     # salva recortes, máscaras e o atlas
```

## Como fotografar

Peça estendida sem ninguém vestindo, luz uniforme, **fundo liso** de cor diferente da peça, frente e costas de
frente (não de perfil), **≥ 1024 px** de largura por vista. Uma folha com várias vistas lado a lado também serve:
as vistas são separadas da esquerda para a direita (frente, costas, depois as outras, ainda não usadas).
Fotos abaixo de 400 px por vista geram aviso: a textura sai borrada.

## Como funciona

1. **Recorte:** distância Lab ao fundo (mediana das bordas). Fundo liso é premissa.
2. **Silhueta:** acha a axila (onde a manga se solta do tronco), as bordas do tronco por linha e o eixo raiz→barra de
   cada manga.
3. **Achatar no molde:** o template tem UV planar (frente na metade esquerda do atlas, costas na direita). Cada
   linha do molde do tronco é esticada sobre a linha correspondente do tronco na foto; cada tubo de manga é mapeado
   sobre o retângulo da manga na foto, alinhado ao eixo raiz→barra.
4. **Bordas:** a franja de mistura com o fundo é erodida e o fora da peça é preenchido com a cor vizinha, para não
   aparecer contorno do fundo na textura.
5. **Saída:** atlas PNG embutido no GLB (`baseColorTexture`); o shader o multiplica pela luz estimada (T10).

## Limitações

- A forma vem do template (camiseta de manga curta). A textura se adapta; a silhueta 3D não copia a da foto.
- Detalhes na manga saem deformados: o retângulo da manga na foto é diagonal e o tubo do template é reto.
- As vistas laterais da folha (mangas de lado) ainda não entram; servirão para o topo das mangas.
- Sem tratamento de sombras pintadas na foto: elas ficam na textura e se somam à luz do app.
- No modo espelho (padrão) os textos da peça aparecem invertidos, como num espelho de verdade; `--no-mirror`
  mostra a imagem crua e legível.
- **Marcas:** as fotos (`assets/photos/`) e os GLBs `photo_*` ficam fora do git por conter logotipos.
