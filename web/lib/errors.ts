// Traduz erros técnicos (do navegador, da rede, do SDK da Decart) para mensagens que o visitante do estande
// entende (CLAUDE.md 4.4: "nunca tela branca ou erro técnico"). Best-effort: sem correspondência conhecida,
// cai numa mensagem genérica — nunca mostra o texto técnico bruto na tela.
export function friendlyErrorMessage(raw: string | null): string | null {
  if (!raw) return null;
  const low = raw.toLowerCase();
  if (low.includes("permission") || low.includes("notallowed") || low.includes("negada")) {
    return "Não conseguimos acessar a câmera. Verifique as permissões do navegador e tente de novo.";
  }
  if (low.includes("notfound") || low.includes("devices")) {
    return "Não encontramos uma câmera conectada. Chame um responsável pelo estande.";
  }
  if (low.includes("fetch") || low.includes("network") || low.includes("token") || low.includes("failed to")) {
    return "Problema de conexão. Verifique a internet e tente de novo.";
  }
  return "Algo deu errado. Tente de novo.";
}
