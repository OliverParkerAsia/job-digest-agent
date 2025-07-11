import json

def prepare_finetune_dataset(
    input_log_path="logs.jsonl",
    output_path="training_set.jsonl",
    min_lines=3,
    max_lines=12
):
    with open(input_log_path, "r", encoding="utf-8") as infile, \
         open(output_path, "w", encoding="utf-8") as outfile:

        for line in infile:
            entry = json.loads(line)

            prompt = entry.get("prompt", "").strip()
            completion = entry.get("completion", "").strip()

            lines = completion.split("\n")
            if not (min_lines <= len(lines) <= max_lines):
                continue  # skip incomplete or bloated completions

            # Normalize formatting (OpenPipe wants chat messages)
            record = {
                "messages": [
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": completion}
                ]
            }

            outfile.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"✅ Done. Saved to: {output_path}")
