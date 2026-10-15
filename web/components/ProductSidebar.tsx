"use client";

import { useEffect, useRef } from "react";
import { PRODUCTS, Product } from "@/lib/catalog";
import Image from "next/image";

interface ProductSidebarProps {
  activeProduct: Product | null;
  onSelectProduct: (product: Product) => void;
  /** Peça em foco para a navegação por gestos/teclado (anel branco); null = sem sessão ativa. */
  focusedProductId?: string | null;
}

export function ProductSidebar({
  activeProduct,
  onSelectProduct,
  focusedProductId = null,
}: ProductSidebarProps) {
  const focusedRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    focusedRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [focusedProductId]);

  return (
    <aside className="w-[26rem] shrink-0 border-r border-gray-800 bg-brand-navy-dark flex flex-col portrait:w-full portrait:h-[38vh] portrait:border-r-0 portrait:border-t">
      <div className="p-6 border-b border-gray-800 portrait:flex portrait:items-center portrait:gap-6 portrait:py-4">
        <div className="mb-4 inline-block rounded-lg bg-white px-3 py-2 portrait:mb-0 portrait:shrink-0">
          <Image
            src="/brand/senai-lab-fashion.png"
            alt="SENAI Lab Fashion"
            width={430}
            height={124}
            className="h-auto w-[170px]"
          />
        </div>
        <h2 className="font-semibold text-2xl">Peças</h2>
        <p className="text-lg text-gray-400 mt-1">
          Toque numa peça para experimentar
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-2 gap-4 portrait:grid-cols-4">
          {PRODUCTS.map((product) => (
            <button
              key={product.id}
              ref={focusedProductId === product.id ? focusedRef : undefined}
              onClick={() => onSelectProduct(product)}
              className={`text-left rounded-xl overflow-hidden border-4 transition-all ${
                activeProduct?.id === product.id
                  ? "border-brand-orange ring-4 ring-brand-orange/30"
                  : focusedProductId === product.id
                    ? "border-white ring-4 ring-white/50"
                    : "border-gray-700 hover:border-gray-500"
              }`}
            >
              <div className="relative aspect-square bg-white">
                <Image
                  src={product.imagem}
                  alt={product.nome}
                  fill
                  priority
                  className="object-contain p-2"
                  sizes="200px"
                />
              </div>
              <div className="p-3 bg-gray-900">
                <p className="text-lg font-medium leading-snug line-clamp-2 min-h-[2.75em]">
                  {product.nome}
                </p>
              </div>
            </button>
          ))}
          {PRODUCTS.length === 0 && (
            <p className="col-span-full text-lg text-gray-500">
              Nenhuma peça ativa. Edite catalog/products.json.
            </p>
          )}
        </div>
      </div>
    </aside>
  );
}
