# tests/unit/test_tags_util.py
import pytest
from aws_cdk import Stack, App
from reply_cdk_utils.runtime_stacks_tagging import TagsUtil

def test_add_tags():
    # Arrange
    app = App()
    stack = Stack(app, "TestStack")
    test_tags = {
        "Environment": "test",
        "Project": "sow-validator"
    }

    # Act
    added_tags = TagsUtil.add_tags(test_tags, stack)

    # Assert
    assert added_tags == test_tags
    # You can also verify the tags were actually added to the stack
