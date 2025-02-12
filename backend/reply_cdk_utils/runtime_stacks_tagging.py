from aws_cdk import Stack, Tags


# Tags adding class
class TagsUtil:
    def __init__(self, stack):
        self.stack = stack

    @classmethod
    def add_tags(cls, dict_tags: dict, stack: Stack) -> [tuple]:
        """
        A class method that adds tags to a Stack
        """

        # Get the list of tags to be added from the tag factory
        stack_tags_to_add = dict_tags

        # Add the tags to the Stack
        for key_tag, value_tag in stack_tags_to_add.items():
            Tags.of(stack).add(str(key_tag), str(value_tag))

        Tags.of(stack).add("CloudFormationParentName", stack.stack_name)
        return stack_tags_to_add
