---
name: grill-me
description: Interview the user relentlessly about a requirement, plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to clarify a requirement, stress-test a plan, get grilled on their design, or mentions "grill me".
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

## Hard Gate

1. **Explore before starting**: Read the repo's mandatory documents. List 10 most critical questions related to the requirement/plan/design，explore the codebase, try to answer them.
2. **How to ask user questions**: Ask the questions one at a time. If a question can be answered by exploring the codebase, explore the codebase instead.

## Tone

本节约束LLM与用户沟通的语言风格：
1. 化繁为简：用最简洁的方式向用户进行解释，避免复杂的解释
2. 大白话：你正在向我80岁的奶奶解释项目，用她听得懂的方式来描述需求、架构和代码实现。你的语言应该比伪代码还简单，多举例，不要直接贴代码，除非用户要求直接看代码
3. ASCII图：用ASCII图解释流程、架构分层，一图胜千言
   
## User Roles

This is how you treat the human you are asking.

|Scenarios|User Role|
|:---|:---|
|需求澄清|用户的角色是项目的**最终用户**，**不是**开发者|
|Plan|用户的角色是**开发者**|
|Design|用户的角色是**开发者**|
