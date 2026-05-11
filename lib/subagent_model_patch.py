#!/usr/bin/env python3
"""Patch Superpowers subagent prompt templates with configured models."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from subagent_models import load_subagent_model_config

START_PREFIX = '<!-- superpower-adapter:subagent-model:'
END_PREFIX = '<!-- /superpower-adapter:subagent-model:'


@dataclass(frozen=True)
class PromptTemplateSpec:
    subagent_id: str
    relative_path: Path
    expected_text: str

    @property
    def start_marker(self) -> str:
        return f'{START_PREFIX}{self.subagent_id} -->'

    @property
    def end_marker(self) -> str:
        return f'{END_PREFIX}{self.subagent_id} -->'

    def rendered_block(self, model: str, indent: str) -> str:
        return '\n'.join(
            [
                f'{indent}{self.start_marker}',
                f'{indent}model: {model}',
                f'{indent}{self.end_marker}',
            ]
        )


@dataclass(frozen=True)
class FinalReviewerSpec:
    subagent_id: str
    relative_path: Path
    expected_text: str
    insert_before: str

    @property
    def start_marker(self) -> str:
        return f'{START_PREFIX}{self.subagent_id} -->'

    @property
    def end_marker(self) -> str:
        return f'{END_PREFIX}{self.subagent_id} -->'

    def rendered_block(self, model: str) -> str:
        return '\n'.join(
            [
                self.start_marker,
                '## Adapter Final Code Reviewer Model Override',
                '',
                'For the terminal final code-reviewer step after all implementation-plan tasks are complete, use the shared `requesting-code-review/code-reviewer.md` template with this dedicated model route:',
                '',
                '```yaml',
                'Task tool (general-purpose):',
                f'  model: {model}',
                '  description: "Final code review for entire implementation"',
                '  prompt: |',
                '    Use template at requesting-code-review/code-reviewer.md',
                '',
                '    DESCRIPTION: Entire implementation from the executed plan',
                '    PLAN_OR_REQUIREMENTS: Full implementation plan and relevant referenced context',
                '    BASE_SHA: Commit before the first implementation task',
                '    HEAD_SHA: Current commit after all per-task reviews pass',
                '```',
                '',
                'This override applies only to the final whole-implementation review. Per-task code quality reviews continue to use `code-quality-reviewer-prompt.md`; ordinary shared code review continues to use `requesting-code-review/code-reviewer.md`.',
                self.end_marker,
            ]
        )


@dataclass(frozen=True)
class PatchFailure:
    subagent_id: str
    path: Path
    reason: str
    model: str | None = None


SPECS = (
    PromptTemplateSpec(
        subagent_id='spec-document-reviewer',
        relative_path=Path('skills/brainstorming/spec-document-reviewer-prompt.md'),
        expected_text='spec document reviewer',
    ),
    PromptTemplateSpec(
        subagent_id='plan-document-reviewer',
        relative_path=Path('skills/writing-plans/plan-document-reviewer-prompt.md'),
        expected_text='plan document reviewer',
    ),
    PromptTemplateSpec(
        subagent_id='code-reviewer',
        relative_path=Path('skills/requesting-code-review/code-reviewer.md'),
        expected_text='Senior Code Reviewer',
    ),
    PromptTemplateSpec(
        subagent_id='implementer',
        relative_path=Path('skills/subagent-driven-development/implementer-prompt.md'),
        expected_text='Implementer Subagent Prompt Template',
    ),
    PromptTemplateSpec(
        subagent_id='spec-compliance-reviewer',
        relative_path=Path('skills/subagent-driven-development/spec-reviewer-prompt.md'),
        expected_text='Spec Compliance Reviewer',
    ),
    PromptTemplateSpec(
        subagent_id='code-quality-reviewer',
        relative_path=Path('skills/subagent-driven-development/code-quality-reviewer-prompt.md'),
        expected_text='Code Quality Reviewer',
    ),
)

FINAL_CODE_REVIEWER_SPEC = FinalReviewerSpec(
    subagent_id='final-code-reviewer',
    relative_path=Path('skills/subagent-driven-development/SKILL.md'),
    expected_text='Dispatch final code reviewer subagent for entire implementation',
    insert_before='## Example Workflow',
)


def strip_model_block(text: str, spec: PromptTemplateSpec | FinalReviewerSpec) -> tuple[str, bool]:
    start = text.find(spec.start_marker)
    if start == -1:
        return text, False
    end = text.find(spec.end_marker, start)
    if end == -1:
        raise ValueError(f'malformed adapter model marker for {spec.subagent_id}: missing end marker')
    end += len(spec.end_marker)
    if end < len(text) and text[end:end + 1] == '\n':
        end += 1
    if start > 0 and text[start - 1:start] == '\n':
        start -= 1
    return text[:start] + text[end:], True


def find_task_insert(text: str, spec: PromptTemplateSpec) -> tuple[int, str]:
    if spec.expected_text not in text:
        raise ValueError(f'expected prompt identity text not found: {spec.expected_text}')

    lines = text.splitlines(keepends=True)
    in_fence = False
    fence = ''
    fence_start = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not in_fence and stripped.startswith('```'):
            in_fence = True
            fence = stripped[:3]
            fence_start = index
            continue
        if in_fence and stripped.startswith(fence):
            block = ''.join(lines[fence_start:index + 1])
            try:
                relative_insert, indent = find_insert_in_block(block, spec)
            except ValueError:
                in_fence = False
                fence = ''
                continue
            absolute_insert = sum(len(item) for item in lines[:fence_start]) + relative_insert
            return absolute_insert, indent
    raise ValueError('could not find fenced Task template with description and prompt')


def find_insert_in_block(block: str, spec: PromptTemplateSpec) -> tuple[int, str]:
    if 'Task tool' not in block and 'Task(' not in block:
        raise ValueError('not a Task template block')
    lines = block.splitlines(keepends=True)
    description_index = None
    prompt_index = None
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if description_index is None and stripped.startswith('description:'):
            description_index = index
        if stripped.startswith('prompt: |'):
            prompt_index = index
            break
    if description_index is not None and prompt_index is not None and prompt_index > description_index:
        indent = lines[description_index][: len(lines[description_index]) - len(lines[description_index].lstrip())]
        insert_at = sum(len(item) for item in lines[:description_index + 1])
        return insert_at, indent

    task_index = None
    for index, line in enumerate(lines):
        if 'Task tool' in line:
            task_index = index
            break
    if task_index is None:
        raise ValueError('Task block lacks description before prompt')
    task_indent = lines[task_index][: len(lines[task_index]) - len(lines[task_index].lstrip())]
    indent = task_indent + '  '
    for line in lines[task_index + 1:]:
        if line.strip():
            indent = line[: len(line) - len(line.lstrip())]
            break
    insert_at = sum(len(item) for item in lines[:task_index + 1])
    return insert_at, indent


def apply_spec(path: Path, spec: PromptTemplateSpec, model: str) -> tuple[bool, str]:
    text = path.read_text(encoding='utf-8')
    text, removed = strip_model_block(text, spec)
    insert_at, indent = find_task_insert(text, spec)
    block = spec.rendered_block(model, indent)
    updated = text[:insert_at] + block + '\n' + text[insert_at:]
    if updated != path.read_text(encoding='utf-8'):
        path.write_text(updated, encoding='utf-8')
        return True, f'Configured subagent model: {spec.subagent_id} -> {model}'
    return removed, f'Configured subagent model already satisfied: {spec.subagent_id} -> {model}'


def remove_spec(path: Path, spec: PromptTemplateSpec | FinalReviewerSpec) -> bool:
    if not path.is_file():
        return False
    text = path.read_text(encoding='utf-8')
    updated, removed = strip_model_block(text, spec)
    if removed:
        path.write_text(updated, encoding='utf-8')
    return removed


def verify_spec(path: Path, spec: PromptTemplateSpec, model: str | None) -> None:
    if not path.is_file():
        raise ValueError('target file is missing')
    text = path.read_text(encoding='utf-8')
    if model is None:
        if spec.start_marker in text or spec.end_marker in text:
            raise ValueError('adapter model marker remains but no model is configured')
        return
    if spec.rendered_block(model, '') in text:
        return
    if f'model: {model}' in text and spec.start_marker in text and spec.end_marker in text:
        return
    raise ValueError(f'configured model was not applied: {model}')


def find_final_reviewer_insert(text: str, spec: FinalReviewerSpec) -> int:
    if spec.expected_text not in text:
        raise ValueError(f'expected prompt identity text not found: {spec.expected_text}')
    insert_at = text.find(spec.insert_before)
    if insert_at == -1:
        raise ValueError(f'could not find insertion heading: {spec.insert_before}')
    if insert_at > 0 and text[insert_at - 1:insert_at] == '\n':
        insert_at -= 1
    return insert_at


def apply_final_reviewer_spec(path: Path, spec: FinalReviewerSpec, model: str) -> tuple[bool, str]:
    text = path.read_text(encoding='utf-8')
    text, removed = strip_model_block(text, spec)
    insert_at = find_final_reviewer_insert(text, spec)
    block = spec.rendered_block(model)
    updated = text[:insert_at] + '\n\n' + block + '\n\n' + text[insert_at:].lstrip('\n')
    if updated != path.read_text(encoding='utf-8'):
        path.write_text(updated, encoding='utf-8')
        return True, f'Configured subagent model: {spec.subagent_id} -> {model}'
    return removed, f'Configured subagent model already satisfied: {spec.subagent_id} -> {model}'


def verify_final_reviewer_spec(path: Path, spec: FinalReviewerSpec, model: str | None) -> None:
    if not path.is_file():
        raise ValueError('target file is missing')
    text = path.read_text(encoding='utf-8')
    if model is None:
        if spec.start_marker in text or spec.end_marker in text:
            raise ValueError('adapter model marker remains but no model is configured')
        return
    if spec.start_marker in text and spec.end_marker in text and f'model: {model}' in text:
        return
    raise ValueError(f'configured model was not applied: {model}')


def format_failures(failures: list[PatchFailure], mode: str) -> str:
    lines = [f'Subagent model {mode} failed for {len(failures)} configured subagent(s):']
    for failure in failures:
        model = f' model={failure.model}' if failure.model else ''
        lines.append(f'- {failure.subagent_id}{model}: {failure.path} — {failure.reason}')
    lines.append('Superpowers may have changed these prompt templates; update superpower-adapter subagent model patch specs.')
    return '\n'.join(lines)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('Usage: subagent_model_patch.py <install|uninstall|verify> <superpowers-dir>')

    mode = sys.argv[1]
    target = Path(sys.argv[2]).resolve()
    if mode not in {'install', 'uninstall', 'verify'}:
        raise SystemExit(f'Unsupported mode: {mode}')

    root = Path(__file__).resolve().parents[1]
    config = load_subagent_model_config(root)
    failures: list[PatchFailure] = []
    changed = False

    for spec in SPECS:
        path = target / spec.relative_path
        model = config.upstream_prompt_templates.get(spec.subagent_id)
        try:
            if mode == 'install':
                if path.is_file():
                    removed = remove_spec(path, spec)
                    changed = changed or removed
                if model is not None:
                    if not path.is_file():
                        raise ValueError('target file is missing')
                    spec_changed, message = apply_spec(path, spec, model)
                    changed = changed or spec_changed
                    print(message)
            elif mode == 'uninstall':
                changed = remove_spec(path, spec) or changed
            else:
                if model is None and not config.has_effective_upstream_models:
                    if path.is_file():
                        text = path.read_text(encoding='utf-8')
                        if spec.start_marker in text or spec.end_marker in text:
                            failures.append(
                                PatchFailure(
                                    spec.subagent_id,
                                    path,
                                    'adapter model marker remains but no model is configured',
                                    model,
                                )
                            )
                    continue
                verify_spec(path, spec, model)
        except ValueError as exc:
            if model is not None or (mode == 'verify' and config.has_effective_upstream_models):
                failures.append(PatchFailure(spec.subagent_id, path, str(exc), model))

    final_spec = FINAL_CODE_REVIEWER_SPEC
    final_path = target / final_spec.relative_path
    final_model = config.upstream_prompt_templates.get('final-code-reviewer')
    if final_model is None:
        final_model = config.upstream_prompt_templates.get('code-reviewer')
    try:
        if mode == 'install':
            if final_path.is_file():
                removed = remove_spec(final_path, final_spec)
                changed = changed or removed
            if final_model is not None:
                if not final_path.is_file():
                    raise ValueError('target file is missing')
                spec_changed, message = apply_final_reviewer_spec(final_path, final_spec, final_model)
                changed = changed or spec_changed
                print(message)
        elif mode == 'uninstall':
            changed = remove_spec(final_path, final_spec) or changed
        else:
            if final_model is None and not config.has_effective_upstream_models:
                if final_path.is_file():
                    text = final_path.read_text(encoding='utf-8')
                    if final_spec.start_marker in text or final_spec.end_marker in text:
                        failures.append(
                            PatchFailure(
                                final_spec.subagent_id,
                                final_path,
                                'adapter model marker remains but no model is configured',
                                final_model,
                            )
                        )
            else:
                verify_final_reviewer_spec(final_path, final_spec, final_model)
    except ValueError as exc:
        if final_model is not None or (mode == 'verify' and config.has_effective_upstream_models):
            failures.append(PatchFailure(final_spec.subagent_id, final_path, str(exc), final_model))

    if failures:
        raise SystemExit(format_failures(failures, mode))

    if mode == 'verify':
        print('Subagent model patches OK')
    elif changed:
        print(f'Subagent model patches updated via {mode}')
    else:
        print(f'Subagent model patches already satisfied for {mode}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
