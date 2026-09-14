import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[2]
PRODUCT_SCHEMA_PATHS = [
    ROOT / 'schemas/v1/verified-action-object.schema.json',
    ROOT / 'schemas/v1/action-graph.schema.json',
]
BENCHMARK_SCHEMA_PATH = ROOT / 'benchmark/schema/campus-action-bench-v1.schema.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def test_all_m1_schemas_load_offline_and_are_valid_draft_2020_12_documents():
    for path in [*PRODUCT_SCHEMA_PATHS, BENCHMARK_SCHEMA_PATH]:
        schema = load(path)
        Draft202012Validator.check_schema(schema)
        assert schema['$schema'].endswith('draft/2020-12/schema')


def test_development_samples_fit_the_benchmark_container():
    validator = Draft202012Validator(load(BENCHMARK_SCHEMA_PATH), format_checker=FormatChecker())
    samples = [
        json.loads(line)
        for line in (ROOT / 'benchmark/dev_samples.jsonl').read_text(encoding='utf-8').splitlines()
        if line.strip()
    ]
    assert samples
    assert all(not list(validator.iter_errors(sample)) for sample in samples)


def test_benchmark_can_carry_a_protocol_graph_without_redefining_it():
    benchmark_validator = Draft202012Validator(load(BENCHMARK_SCHEMA_PATH))
    sample = json.loads((ROOT / 'benchmark/dev_samples.jsonl').read_text(encoding='utf-8').splitlines()[0])
    sample['gold']['protocol_action_graph'] = load(ROOT / 'examples/action-graphs/branch-and-revision.json')
    assert not list(benchmark_validator.iter_errors(sample))


def test_benchmark_does_not_redefine_protocol_verification_states():
    benchmark = load(BENCHMARK_SCHEMA_PATH)
    gold_properties = benchmark['properties']['gold']['properties']
    annotation_properties = benchmark['properties']['annotation']['properties']
    assert 'verification_status' not in gold_properties
    assert 'verification_status' not in annotation_properties
    assert set(gold_properties['relevance']['enum']) == {'relevant', 'not_relevant', 'uncertain'}


def test_product_and_benchmark_version_boundaries_are_explicit():
    vao = load(PRODUCT_SCHEMA_PATHS[0])
    graph = load(PRODUCT_SCHEMA_PATHS[1])
    benchmark = load(BENCHMARK_SCHEMA_PATH)
    assert vao['properties']['schema_version']['const'] == 'verified-action-object/v1'
    assert graph['properties']['schema_version']['const'] == 'action-graph/v1'
    assert benchmark['title'].startswith('CampusActionBench v1')
