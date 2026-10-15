"""Frozen template declarations control artifact naming without operation cases."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from local_providers.artifact_metadata import artifact_metadata


class ArtifactMetadataTests(unittest.TestCase):
    def test_legacy_and_declared_formats(self):
        self.assertEqual(artifact_metadata('vlan {{ vlan_id }}')['extension'], '.txt')
        for fmt, language, extension in [('native_cli', 'ios', '.cfg'), ('structured', 'json', '.json')]:
            template = '{# artifact: {"format":"%s","language":"%s","extension":"%s"} #}\ncontent' % (fmt, language, extension)
            self.assertEqual(artifact_metadata(template), dict(format=fmt, language=language, extension=extension))

    def test_rejects_invalid_declarations(self):
        for value in ['[]', '{"format":"native_cli"}', '{"format":"native_cli","language":"ios","extension":"../../x"}', '{"format":"native_cli","language":"ios","extension":".cfg","extra":true}']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                artifact_metadata('{# artifact: '+value+' #}')


if __name__ == '__main__':
    unittest.main()
