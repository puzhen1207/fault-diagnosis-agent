# Fault Diagnosis Graph

```mermaid
flowchart TD
    A[故障分类与实体抽取] --> B{信息是否充足}
    B -- 否 --> C[追问补充信息]
    B -- 是 --> D[混合检索]
    D --> E[根因分析]
    E --> F[处置方案生成]
    F --> G[最终回答]
```

