// Imprime uma única imagem (data URL) sem imprimir o resto da página, sem biblioteca nova: cria um bloco
// temporário visível só em @media print, chama window.print() e remove tudo depois. A foto nunca sai da
// máquina do quiosque nem passa por rede - vai direto do canvas para a impressora (CLAUDE.md 4.5b).
export function printImage(dataUrl: string): void {
  const container = document.createElement("div");
  container.id = "print-photo-area";
  const img = document.createElement("img");
  img.src = dataUrl;
  container.appendChild(img);

  const style = document.createElement("style");
  style.textContent = `
    #print-photo-area { display: none; }
    @media print {
      body * { visibility: hidden; }
      #print-photo-area, #print-photo-area img { visibility: visible; }
      #print-photo-area { display: block; position: fixed; inset: 0; margin: 0; padding: 0; }
      #print-photo-area img { width: 100%; height: 100%; object-fit: contain; }
    }
  `;

  document.body.append(style, container);

  const cleanup = () => {
    container.remove();
    style.remove();
    window.removeEventListener("afterprint", cleanup);
  };
  window.addEventListener("afterprint", cleanup);
  // "afterprint" nem sempre dispara de forma confiável em todo navegador; garante a limpeza de qualquer jeito.
  setTimeout(cleanup, 60_000);

  window.print();
}
