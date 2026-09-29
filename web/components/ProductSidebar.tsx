"use client";

import { PRODUCTS, Product } from "@/lib/catalog";
import Image from "next/image";

interface ProductSidebarProps {
  activeProduct: Product | null;
  onSelectProduct: (product: Product) => void;
}

export function ProductSidebar({
  activeProduct,
  onSelectProduct,
}: ProductSidebarProps) {
  return (
    <aside className="w-[26rem] shrink-0 border-r border-gray-800 bg-gray-900 flex flex-col">
      <div className="p-6 border-b border-gray-800">
        <h2 className="font-semibold text-2xl">Peças</h2>
        <p className="text-lg text-gray-400 mt-1">
          Toque numa peça para experimentar
        </p>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-2 gap-4">
          {PRODUCTS.map((product) => (
            <button
              key={product.id}
              onClick={() => onSelectProduct(product)}
              className={`text-left rounded-xl overflow-hidden border-4 transition-all ${
                activeProduct?.id === product.id
                  ? "border-blue-500 ring-4 ring-blue-500/30"
                  : "border-gray-700 hover:border-gray-500"
              }`}
            >
              <div className="relative aspect-square bg-gray-800">
                <Image
                  src={product.imagem}
                  alt={product.nome}
                  fill
                  priority
                  className="object-cover"
                  sizes="200px"
                />
              </div>
              <div className="p-3 bg-gray-900">
                <p className="text-lg font-medium truncate">{product.nome}</p>
              </div>
            </button>
          ))}
          {PRODUCTS.length === 0 && (
            <p className="col-span-2 text-lg text-gray-500">
              Nenhuma peça ativa. Edite catalog/products.json.
            </p>
          )}
        </div>
      </div>
    </aside>
  );
}
