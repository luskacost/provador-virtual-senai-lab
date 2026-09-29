import type { Metadata } from "next";
import "./globals.css";

// Provisório: nome do projeto, sem identidade visual do laboratório ainda (logo/cores virão do usuário).
export const metadata: Metadata = {
  title: "Provador Virtual",
  description: "Experimente peças do laboratório ao vivo, na frente da câmera.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="antialiased bg-gray-950 text-white">{children}</body>
    </html>
  );
}
