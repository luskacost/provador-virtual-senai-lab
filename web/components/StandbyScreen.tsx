"use client";

import Image from "next/image";

// Tela de standby (Shift+S): cobre tudo, só o logo, fundo preto (não gasta nada e poupa a TV ligada o
// dia todo). O logo tem "FASHION" em preto, por isso fica numa placa branca, como nas outras telas.
export function StandbyScreen() {
  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black">
      <div className="rounded-2xl bg-white px-10 py-6">
        <Image
          src="/brand/senai-lab-fashion.png"
          alt="SENAI Lab Fashion"
          width={430}
          height={124}
          className="h-auto w-[320px] sm:w-[440px]"
          priority
        />
      </div>
    </div>
  );
}
