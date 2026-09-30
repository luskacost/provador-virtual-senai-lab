// Catálogo do provador (CLAUDE.md, seção 4.1). Fonte única: catalog/products.json — adicionar ou remover
// peça é editar esse JSON e colocar a imagem em public/catalog/. Nada de tela de cadastro.
import catalogData from "@/catalog/products.json";

export interface Product {
  id: string;
  nome: string;
  /** Livre por enquanto; ainda sem filtro por categoria na interface. O catálogo vai cobrir do vestuário
   * formal ao EPI (roupa comum, uniforme, EPI de cabeça/mãos/corpo) — usar valores como "top", "formal",
   * "epi-cabeca", "epi-maos", "epi-corpo" conforme as peças forem chegando. */
  categoria: string;
  /** Caminho em public/, ex.: "/catalog/arquivo.jpg". Fundo limpo, sem pessoa, >=512px (guia de fotos da Decart). */
  imagem: string;
  /** Em inglês, padrão "substitute"/"add" da Decart (ver README de web/ e docs/aprendizados.md). */
  prompt: string;
  /** false esconde a peça sem apagar do catálogo (ex.: testou mal com o modelo). Ausente = ativa. */
  ativo?: boolean;
}

/** Todas as peças, incluindo as com ativo:false. Usado pelas métricas (CLAUDE.md 4.5) para resolver o nome
 * de uma peça experimentada no passado, mesmo que ela tenha sido desativada depois. */
export const ALL_PRODUCTS: Product[] = catalogData as Product[];

export const PRODUCTS: Product[] = ALL_PRODUCTS.filter((p) => p.ativo !== false);
