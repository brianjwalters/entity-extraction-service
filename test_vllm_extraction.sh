#!/bin/bash

curl -X POST http://10.10.0.87:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-72b-awq-128k",
    "messages": [
      {
        "role": "system",
        "content": "You are a legal entity extraction expert. Extract all legal entities and return them as JSON."
      },
      {
        "role": "user",
        "content": "Extract entities from this text: Brown v. Board of Education, 347 U.S. 483 (1954), decided by Chief Justice Earl Warren. Return a JSON object with an entities array."
      }
    ],
    "max_tokens": 1000,
    "temperature": 0.1
  }' --max-time 60 | jq -r '.choices[0].message.content'