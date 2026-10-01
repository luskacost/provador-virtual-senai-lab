# Como adicionar uma peça ao catálogo

Dois passos: colocar a imagem em `web/public/catalog/` e acrescentar uma entrada em
`web/catalog/products.json`. Não precisa reiniciar nada em produção — na próxima vez que alguém abrir a
página, a peça já aparece (em desenvolvimento, o `npm run dev` recarrega sozinho).

## 1. Antes de mais nada: a foto serve?

Confira **antes** de usar qualquer imagem:

| Pergunta | Se a resposta for sim... |
|---|---|
| Tem marca d'água (ex.: "pngtree", "shutterstock")? | **Não usar.** Foto de banco de imagem sem licença. |
| Tem etiqueta/logo de loja visível (Zara, H&M, Massimo Dutti, PIECES...)? | **Não usar.** É fotografia comercial de outra marca — tirar a logo não resolve, o problema é a foto em si, não a logo (ver `docs/aprendizados.md`). |
| Parece gerada por IA (textura/bordado fantasiosos demais, impossíveis numa peça costurada)? | **Não usar**, a menos que seja intencional e você confirme. |
| É uma peça lisa, sem marca, sem etiqueta visível, fundo limpo? | Pode usar — risco bem menor. |
| É uma foto sua, de uma peça real do laboratório? | **Melhor opção.** Sempre preferível às outras. |

O ideal continua sendo fotografar a peça real (como a Camiseta SESI e o Colete de Alta Visibilidade):
fundo liso (parede, lençol, papel), boa luz, peça sozinha (sem ninguém vestindo), **pelo menos 512×512
pixels** — quanto maior, melhor o resultado do modelo.

## 2. Salve a imagem

```
web/public/catalog/<slug-da-peca>.jpg
```

Use um nome em kebab-case (letras minúsculas, hífens), sem espaços ou acentos — vai virar parte da URL.
Exemplos já no catálogo: `sesi-camiseta-branca.jpg`, `colete-alta-visibilidade.jpg`.

## 3. Adicione a entrada em `web/catalog/products.json`

```json
{
  "id": "slug-da-peca",
  "nome": "Nome em Português, do Jeito que Aparece na Tela",
  "categoria": "top",
  "imagem": "/catalog/slug-da-peca.jpg",
  "prompt": "Substitute the current top with a ... (em inglês, ver guia abaixo)",
  "ativo": true
}
```

- **`id`**: mesmo slug do nome do arquivo (sem `.jpg`). Precisa ser único no catálogo.
- **`categoria`**: ainda sem filtro na interface, mas organiza para o futuro. Valores sugeridos (a
  proposta é cobrir do vestuário formal ao EPI — ver `docs/aprendizados.md`):
  `top`, `formal`, `epi-cabeca`, `epi-maos`, `epi-corpo`.
- **`imagem`**: sempre começando com `/catalog/` — é o caminho público, não o caminho do arquivo no disco.
- **`ativo`**: comece com `false` se quiser testar antes de liberar para o público (a peça fica no
  catálogo mas não aparece na interface — ver `lib/catalog.ts`). Mude para `true` depois de testar bem.
  Omitir o campo equivale a `true`.

## 4. Escrevendo o prompt (sempre em inglês)

Padrão da Decart: **substitua** uma peça existente, ou **adicione** algo que a pessoa não está usando.

| Padrão | Quando usar | Exemplo |
|---|---|---|
| `Substitute the current top with...` | Troca de camisa/jaqueta/blazer | `"Substitute the current top with a white linen shirt with a relaxed fit"` |
| `Substitute the current headwear with...` | Boné, capacete, gorro | `"Substitute the current headwear with a white hard hat with a chin strap"` |
| `Add ... to the person's ...` | Algo que a pessoa não está vestindo (acessório) | `"Add a pair of clear safety glasses to the person's face"` |

Seja específico: cor, material, textura, padrão, caimento. Mire em 20–30 palavras. Use "the current top" /
"the current headwear" em vez de descrever a roupa atual da pessoa (você não sabe o que ela está vestindo).

```
✅ "Substitute the current top with a sage green crewneck t-shirt with a relaxed regular fit and no print"
❌ "Green shirt"                                    (sem contexto, sem caimento)
❌ "Put a nice shirt on the person"                  (vago - sem cor, material, caimento)
```

## 5. Teste antes de liberar (`"ativo": true`)

Rode `npm run dev`, abra o app, selecione a peça com uma pessoa de verdade na câmera. Preste atenção em:
- O resultado parece a peça real, ou o modelo "inventou" algo muito diferente?
- Mangas, gola, bordas aparecem bem, sem tremer ou distorcer muito?
- Se for EPI pequeno (óculos, luvas), funcionou razoavelmente? Esses são mais arriscados (ver
  `docs/aprendizados.md`, seção "Direção do catálogo").

Se ficou ruim, ponha `"ativo": false` em vez de apagar a entrada — guarda o histórico sem mostrar ao
público (e as métricas antigas dessa peça continuam resolvendo o nome certo, mesmo desativada).
