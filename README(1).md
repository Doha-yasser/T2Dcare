# 🩸 Diabetes RAG Assistant

> An AI-powered, source-grounded assistant that helps adults aged 25–40 who have been recently diagnosed with Type 2 Diabetes understand reliable medical information in simple Egyptian Arabic.

## 📌 Overview

Medical information about Type 2 Diabetes can be complex and difficult for newly diagnosed patients to understand.

This project aims to build a **Retrieval-Augmented Generation (RAG)** system that retrieves relevant information from **NICE (National Institute for Health and Care Excellence)** guidance and uses an LLM to provide clear, easy-to-understand explanations in **Egyptian Arabic**.

The system is designed for educational and informational purposes and does not replace professional medical advice.

---

## 🎯 Target Audience

**Adults aged 25–40 who have been recently diagnosed with Type 2 Diabetes.**

The target audience was selected to focus the system on newly diagnosed adults who need accessible explanations of their condition, lifestyle considerations, and medical terminology.

> **Important:** The target age range describes the intended users of the application. The medical guidance itself is based on NICE guidance for adults and is not limited to ages 25–40.

---

## 🎯 Project Scope

### ✅ In Scope

- Understanding Type 2 Diabetes
- Common symptoms and signs
- Risk factors
- Nutrition and healthy lifestyle education
- Physical activity
- Blood glucose concepts
- HbA1c explanation
- Common diabetes-related complications
- General management information
- Explanation of medical terminology
- Source-grounded medical Q&A
- Responses in simple Egyptian Arabic
- Providing NICE references for answers

### ❌ Out of Scope

- Diagnosing diseases
- Prescribing medications
- Recommending medication dosages
- Providing personalized treatment plans
- Replacing healthcare professionals
- Making emergency medical decisions

---

## 🧠 Why RAG?

Large Language Models can generate fluent and convincing answers that may contain inaccurate or unsupported medical information.

RAG helps address this by retrieving relevant information from a curated medical knowledge base before generating the answer.

### RAG Flow

```text
User Question
      ↓
Query Processing
      ↓
Information Retrieval
      ↓
Relevant NICE Content
      ↓
Context + User Question
      ↓
LLM
      ↓
Safety / Validation
      ↓
Egyptian Arabic Response
      ↓
NICE Source / Citation
```

---

## 📚 Knowledge Source

The initial knowledge base is built from **NICE (National Institute for Health and Care Excellence)** guidance.

### Primary Source

- [NICE — Type 2 Diabetes in Adults: Management](https://www.nice.org.uk/guidance/ng28)

NICE provides evidence-based guidance for healthcare professionals and patients.

The source material may be in **English**, while the generated responses are provided in **Egyptian Arabic**.

---

## 🏗️ Architecture

The system architecture follows the principles of the **C4 Model**, using different levels of abstraction to describe the system.

### Architecture Levels

1. **System Context** — users, actors, and external systems
2. **Container** — major application services and databases
3. **Component** — internal components of the RAG service
4. **Code** — implementation details when required

---

## 👥 Actors

### Primary Actor

**Patient / User**

A newly diagnosed adult aged 25–40 who interacts with the Diabetes RAG Assistant by asking questions about Type 2 Diabetes.

### Supporting Actor

**System Administrator**

Responsible for maintaining and updating the medical knowledge base when required.

### External System

**NICE**

Provides the trusted medical guidance used as the knowledge source.

### External AI Service

**LLM Provider**

Generates the final response using the retrieved NICE context.

---

## 🔷 High-Level Architecture

```text
                 ┌──────────────────────┐
                 │   Patient / User     │
                 │      Age 25–40       │
                 └──────────┬───────────┘
                            │
                            │ Questions
                            ▼
                 ┌──────────────────────┐
                 │ Diabetes RAG         │
                 │ Assistant            │
                 └──────────┬───────────┘
                            │
                 ┌──────────┴───────────┐
                 │                      │
                 ▼                      ▼
        ┌────────────────┐      ┌────────────────┐
        │ NICE Knowledge │      │  LLM Provider  │
        │     Source     │      │                │
        └────────────────┘      └────────────────┘
```

---

## 🔬 Low-Level RAG Architecture

### 📥 Knowledge Ingestion Pipeline

```text
NICE Guidance
      ↓
Document Loader
      ↓
Text Cleaning
      ↓
Chunking
      ↓
Embedding Model
      ↓
Vector Database
```

### 📤 Query & Generation Pipeline

```text
User Question
      ↓
Query Processing
      ↓
Retriever
      ↓
Vector Database
      ↓
Relevant NICE Chunks
      ↓
Prompt Builder
      ↓
LLM
      ↓
Safety / Guardrails
      ↓
Egyptian Arabic Response
      ↓
NICE Citation
```

---

## 🔄 End-to-End System Flow

```text
                    KNOWLEDGE INGESTION

                 NICE Guidance
                       │
                       ▼
                Document Loader
                       │
                       ▼
                 Text Cleaning
                       │
                       ▼
                    Chunking
                       │
                       ▼
                Embedding Model
                       │
                       ▼
                 Vector Database
                       │
                       │
                       ▼
                     QUERY

                 Patient / User
                       │
                       ▼
                 User Question
                       │
                       ▼
                Query Processing
                       │
                       ▼
                   Retriever
                       │
                       ▼
              Relevant NICE Chunks
                       │
                       ▼
                 Prompt Builder
                       │
                       ▼
                      LLM
                       │
                       ▼
              Safety / Guardrails
                       │
                       ▼
            Egyptian Arabic Answer
                       │
                       ▼
                NICE Citation
```

---

## 🔐 Medical Safety

The system is designed as an **educational assistant**, not a diagnostic or treatment system.

The assistant should:

- Ground answers in NICE guidance.
- Avoid making diagnoses.
- Avoid prescribing medication.
- Avoid providing medication dosages.
- Avoid generating unsupported medical claims.
- Communicate uncertainty when appropriate.
- Encourage users to consult qualified healthcare professionals when appropriate.
- Escalate potentially serious situations instead of attempting to manage them autonomously.

---

## 🛠️ Technology Stack

The final technology stack may be updated during development.

Potential components include:

- **Python**
- **LangChain / LlamaIndex**
- **Embedding Model**
- **Vector Database**
- **LLM**
- **FastAPI**
- **Web Interface**
- **RAG Evaluation Tools**

---

## 📂 Project Structure

```text
diabetes-rag-assistant/
│
├── data/
│   ├── raw/
│   └── processed/
│
├── src/
│   ├── ingestion/
│   ├── retrieval/
│   ├── generation/
│   ├── safety/
│   └── evaluation/
│
├── app/
│   └── api/
│
├── notebooks/
│
├── tests/
│
├── docs/
│   └── architecture/
│       ├── high-level/
│       └── low-level/
│
├── .env.example
├── requirements.txt
└── README.md
```

---

## 🚀 RAG Pipeline

### 1. Data Collection

Collect relevant Type 2 Diabetes guidance from NICE.

### 2. Preprocessing

Clean and normalize the collected content while preserving important medical context.

### 3. Chunking

Split the documents into meaningful chunks suitable for retrieval.

### 4. Embeddings

Convert document chunks into vector representations.

### 5. Vector Storage

Store the embeddings in a vector database.

### 6. Retrieval

Retrieve the most relevant NICE chunks for each user question.

### 7. Generation

Provide the retrieved context and user question to the LLM to generate a grounded answer.

### 8. Safety Layer

Check the generated response for unsafe medical recommendations, diagnosis, unsupported claims, or other potentially harmful content.

### 9. Response

Return a clear explanation in Egyptian Arabic with the relevant NICE source.

---

## 📊 Evaluation

The system will be evaluated using criteria such as:

- **Retrieval Relevance** — Does the system retrieve relevant NICE content?
- **Answer Correctness** — Is the generated answer medically accurate?
- **Faithfulness** — Is the answer supported by the retrieved context?
- **Context Relevance** — Is the retrieved context useful for the question?
- **Hallucination Rate** — Does the model generate unsupported information?
- **Arabic Response Quality** — Is the Egyptian Arabic clear and understandable?
- **Citation Accuracy** — Does the cited NICE content support the answer?
- **Medical Safety** — Does the system avoid unsafe diagnosis or treatment recommendations?

---

## 🗺️ Architecture Resources

### C4 Model

- [C4 Model](https://c4model.com/)
- [System Context Diagram](https://c4model.com/diagrams/system-context)
- [Container Diagram](https://c4model.com/diagrams/container)
- [Component Diagram](https://c4model.com/diagrams/component)

### Diagram Tools

- [draw.io](https://app.diagrams.net/)
- [draw.io C4 Modelling](https://www.drawio.com/docs/diagram-types/c4-modelling/)
- [draw.io Templates](https://www.drawio.com/docs/manual/templates/)

---

## ⚠️ Disclaimer

This project is intended for **educational and informational purposes only**.

It is not a substitute for professional medical diagnosis, treatment, or advice.

Users should consult qualified healthcare professionals for medical decisions.
