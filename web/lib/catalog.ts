// Catálogo do provador (CLAUDE.md, seção 4.1). Fonte única: catalog/products.json — adicionar ou remover
// peça é editar esse JSON e colocar a imagem em public/catalog/. Nada de tela de cadastro.
import catalogData from "@/catalog/products.json";

export interface Product {
  id: string;
  nome: string;
  /** Livre por enquanto (ex.: "top", "calca", "acessorio"); ainda sem filtro por categoria na interface. */
  categoria: string;
  /** Caminho em public/, ex.: "/catalog/arquivo.jpg". Fundo limpo, sem pessoa, >=512px (guia de fotos da Decart). */
  imagem: string;
  /** Em inglês, padrão "substitute"/"add" da Decart (ver README de web/ e docs/aprendizados.md). */
  prompt: string;
  /** false esconde a peça sem apagar do catálogo (ex.: testou mal com o modelo). Ausente = ativa. */
  ativo?: boolean;
}

const ALL: Product[] = catalogData as Product[];

export const PRODUCTS: Product[] = ALL.filter((p) => p.ativo !== false);
