import { loadSessions, summarize } from "@/lib/metrics";
import { ALL_PRODUCTS } from "@/lib/catalog";

// Lê data/metricas.json a cada acesso — nunca prerenderizar/cachear esta página (CLAUDE.md 4.5: os
// números têm que refletir as sessões reais até agora, não um instantâneo da build).
export const dynamic = "force-dynamic";

const REASON_LABEL: Record<string, string> = {
  pessoa_saiu: "Visitante saiu",
  limite: "Limite de tempo",
  inatividade: "Inatividade",
  visibilidade: "Aba escondida",
  operador: "Operador encerrou",
};

function formatDuration(totalSeconds: number): string {
  const s = Math.round(totalSeconds);
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}min ${s % 60}s`;
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("pt-BR");
}

export default async function MetricasPage() {
  const sessions = await loadSessions();
  const summary = summarize(sessions);
  const nameOf = (id: string) => ALL_PRODUCTS.find((p) => p.id === id)?.nome ?? id;
  const recent = [...sessions].reverse().slice(0, 50);

  return (
    <main className="min-h-screen bg-gray-950 p-8 text-white">
      <h1 className="text-3xl font-bold">Métricas — SENAI Lab Fashion</h1>
      <p className="mt-2 text-gray-400">
        Só dados estruturais de sessão (horário, duração, peças). Nenhum vídeo ou imagem de visitante é
        gravado (CLAUDE.md, seções 4.5 e 4.6).
      </p>

      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-xl bg-gray-900 p-6">
          <p className="text-sm text-gray-400">Total de sessões</p>
          <p className="mt-1 text-4xl font-bold text-brand-orange">{summary.totalSessions}</p>
        </div>
        <div className="rounded-xl bg-gray-900 p-6">
          <p className="text-sm text-gray-400">Duração média</p>
          <p className="mt-1 text-4xl font-bold text-brand-orange">
            {formatDuration(summary.averageDurationSeconds)}
          </p>
        </div>
        <div className="rounded-xl bg-gray-900 p-6">
          <p className="text-sm text-gray-400">Peças distintas experimentadas</p>
          <p className="mt-1 text-4xl font-bold text-brand-orange">{summary.productRanking.length}</p>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <section>
          <h2 className="text-xl font-semibold">Ranking de peças</h2>
          {summary.productRanking.length === 0 ? (
            <p className="mt-2 text-gray-500">Nenhuma peça experimentada ainda.</p>
          ) : (
            <table className="mt-3 w-full text-left">
              <thead>
                <tr className="text-sm text-gray-400">
                  <th className="pb-2">Peça</th>
                  <th className="pb-2 text-right">Vezes</th>
                </tr>
              </thead>
              <tbody>
                {summary.productRanking.map((r) => (
                  <tr key={r.id} className="border-t border-gray-800">
                    <td className="py-2">{nameOf(r.id)}</td>
                    <td className="py-2 text-right font-medium">{r.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>

        <section>
          <h2 className="text-xl font-semibold">Como as sessões terminaram</h2>
          {summary.totalSessions === 0 ? (
            <p className="mt-2 text-gray-500">Nenhuma sessão registrada ainda.</p>
          ) : (
            <table className="mt-3 w-full text-left">
              <thead>
                <tr className="text-sm text-gray-400">
                  <th className="pb-2">Motivo</th>
                  <th className="pb-2 text-right">Sessões</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(summary.endReasonCounts).map(([reason, count]) => (
                  <tr key={reason} className="border-t border-gray-800">
                    <td className="py-2">{REASON_LABEL[reason] ?? reason}</td>
                    <td className="py-2 text-right font-medium">{count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>

      <section className="mt-8">
        <h2 className="text-xl font-semibold">Sessões recentes (até 50)</h2>
        {recent.length === 0 ? (
          <p className="mt-2 text-gray-500">Nenhuma sessão registrada ainda.</p>
        ) : (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="text-gray-400">
                  <th className="pb-2 pr-4">Início</th>
                  <th className="pb-2 pr-4">Duração</th>
                  <th className="pb-2 pr-4">Motivo</th>
                  <th className="pb-2">Peças</th>
                </tr>
              </thead>
              <tbody>
                {recent.map((s, i) => (
                  <tr key={i} className="border-t border-gray-800">
                    <td className="py-2 pr-4 whitespace-nowrap">{formatDateTime(s.startedAt)}</td>
                    <td className="py-2 pr-4 whitespace-nowrap">{formatDuration(s.durationSeconds)}</td>
                    <td className="py-2 pr-4 whitespace-nowrap">
                      {REASON_LABEL[s.endReason] ?? s.endReason}
                    </td>
                    <td className="py-2">
                      {s.products.length ? s.products.map(nameOf).join(", ") : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}
