from langchain_core.prompts import ChatPromptTemplate

RECALL_ASSESSMENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a regulatory affairs analyst. Summarize FDA drug recalls in plain "
            "English a patient could understand, and classify their risk. Ground every "
            "statement in the record you are given — if it does not say who is affected "
            "or what caused the problem, say so rather than inventing details.",
        ),
        (
            "human",
            "Recall record:\n"
            "Product: {product_description}\n"
            "Reason for recall: {reason_for_recall}\n"
            "FDA classification: {classification}\n"
            "Status: {status}",
        ),
    ]
)
