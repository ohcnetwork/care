import math
from unittest import TestCase
from unittest.mock import patch

from care.facility.models.file_upload import FileUpload
from care.utils.csp import config as cs_provider


class FileUploadModelTest(TestCase):
    @patch("boto3.client")
    def test_bulk_delete_objects(self, mock_s3_client):
        s3_keys = ["key1", "key2", "key3"]

        with patch(
            "care.facility.models.file_upload.settings.FILE_UPLOAD_BUCKET",
            "test_bucket",
        ):
            FileUpload.bulk_delete_objects(s3_keys)

        mock_s3_client.assert_called_once_with("s3", **cs_provider.get_client_config())
        mock_s3_client.return_value.delete_objects.assert_called_once_with(
            Bucket="test_bucket",
            Delete={"Objects": [{"Key": key} for key in s3_keys], "Quiet": True},
        )

    def test_batch_iteration(self):
        s3_keys = ["key1", "key2", "key3", "key4", "key5"]
        max_keys_per_batch = 2

        expected_num_of_batches = math.ceil(len(s3_keys) / max_keys_per_batch)
        expected_batch_keys = [["key1", "key2"], ["key3", "key4"], ["key5"]]

        batches = []
        for batch_index in range(expected_num_of_batches):
            start_index = batch_index * max_keys_per_batch
            end_index = min(start_index + max_keys_per_batch, len(s3_keys))
            batch_keys = s3_keys[start_index:end_index]
            batches.append(batch_keys)

        self.assertEqual(len(batches), expected_num_of_batches)
        self.assertEqual(batches, expected_batch_keys)
