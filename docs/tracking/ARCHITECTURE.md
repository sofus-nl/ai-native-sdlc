# Architecture

AI-native SDLC is one tree of Markdown skills in `skills/`, and Claude Code and Codex both load it. It contains no executable code. The router skill `ai-native-sdlc` picks a lane (Fast, Standard, or Controlled) and invokes the next leaf skill. Lifecycle state lives in the consuming repository under `.sdlc/changes/<slug>/`, so work resumes from `state.md` without replaying the conversation.

## Lifecycle

```mermaid
flowchart TD
    R[Request] --> S[ai-native-sdlc router]
    S -->|Fast| F[Inline edit, diff check, focused proof]
    S -->|Standard / Controlled| SH[ai-native-shape: intent, spec]
    SH --> P[ai-native-plan: checkpoint list]
    P -->|human approves plan| B

    subgraph B[ai-native-build: per checkpoint]
        G1[Behavior gate] --> G2[Visual gate, UI only]
        G2 --> G3[Self-review vs acceptance IDs]
        G3 -->|Controlled| CR[ai-native-review checkpoint mode: 2 isolated reviewers]
        CR -->|after checkpoint 1| H[Human approval]
    end

    B -->|all checkpoints done| RV[ai-native-review: full diff]
    RV --> V[ai-native-verify]
    V --> SHIP[ai-native-ship]
    SHIP --> O[ai-native-operate]
    O -->|incident| D[ai-native-debug]
    B -->|unknown failure| D
    D -->|repair at earliest wrong layer| SH
```

A gate that fails sends work back to the layer at fault, and every downstream gate runs again. A fix inside a checkpoint re-runs only the gates it affects.
