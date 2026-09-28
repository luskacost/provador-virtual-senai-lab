export interface Product {
  name: string;
  image: string;
  prompt: string;
  // Opcional: as peças reais do laboratório não têm preço (não são de venda).
  price?: number;
}

export const PRODUCTS: Product[] = [
  {
    // Primeiro teste com peça real (CLAUDE.md, Fase 2). Frente extraída de assets/photos/sesi/folha.jpg,
    // fundo trocado por branco (a Decart recomenda fundo limpo). Falta ainda id/categoria/ativo do
    // catálogo final em JSON.
    name: "Camiseta SESI",
    image: "/products/sesi-camiseta-branca.jpg",
    prompt:
      "Substitute the current top with a white athletic t-shirt featuring a navy blue 'SESI' logo on the chest, blue sleeve cuff text, and a colorful geometric pattern near the hem",
  },
  {
    name: "Decart Beanie",
    image: "/products/decart-beanie.png",
    prompt:
      "Substitute the current headwear with a navy blue knit beanie with a white cross logo on the fold",
    price: 35,
  },
  {
    name: "Decart Bomber Jacket",
    image: "/products/decart-bomber.png",
    prompt:
      "Substitute the current top with a black bomber jacket with a blue cross logo on the chest and a zip front",
    price: 149,
  },
  {
    name: "Decart Cap",
    image: "/products/decart-cap.png",
    prompt:
      'Substitute the current headwear with a black baseball cap with a blue cross logo and "DECART" text',
    price: 29,
  },
  {
    name: "Decart Crewneck",
    image: "/products/decart-crewneck.png",
    prompt:
      'Substitute the current top with a grey crewneck sweatshirt with a large blue cross logo and "DECART" text on the front',
    price: 89,
  },
  {
    name: "Decart Hoodie",
    image: "/products/decart-hoodie.png",
    prompt:
      "Substitute the current top with a navy blue hoodie with a white cross logo on the chest and a kangaroo pocket",
    price: 99,
  },
  {
    name: "Decart Polo",
    image: "/products/decart-polo.png",
    prompt:
      "Substitute the current top with a navy blue polo shirt with a white cross logo on the chest",
    price: 69,
  },
  {
    name: "Decart T-Shirt",
    image: "/products/decart-tshirt.png",
    prompt:
      "Substitute the current top with a navy blue t-shirt with a white cross logo on the chest",
    price: 45,
  },
  {
    name: "Decart Zip-Up Hoodie",
    image: "/products/decart-zipup.png",
    prompt:
      "Substitute the current top with a black zip-up hoodie with a blue cross logo on the chest",
    price: 109,
  },
  {
    name: "Decart Rain Jacket",
    image: "/products/decart-rainjacket.png",
    prompt:
      "Substitute the current top with a yellow hooded rain jacket with a grey Decart cross logo on the chest and zip front",
    price: 129,
  },
  {
    name: "Decart Blazer",
    image: "/products/decart-blazer.png",
    prompt:
      "Substitute the current top with a navy blue blazer with a white Decart cross logo on the chest, worn over a light blue dress shirt and navy tie",
    price: 199,
  },
];
