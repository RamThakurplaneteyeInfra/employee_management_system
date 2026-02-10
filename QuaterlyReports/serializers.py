from rest_framework import serializers
from .models import Functions, FunctionsGoals, ActionableGoals,FunctionsEntries
from task_management.models import TaskStatus

class ActionableGoalSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActionableGoals
        fields = ['id', 'purpose', 'grp']

class FunctionGoalSerializer(serializers.ModelSerializer):
    # This fetches all ActionableGoals related to this FunctionGoal
    actionable_goals = ActionableGoalSerializer(source='actionablegoals_set', many=True, read_only=True)

    class Meta:
        model = FunctionsGoals
        fields = ['id', 'Maingoal', 'actionable_goals']

class FunctionDetailSerializer(serializers.ModelSerializer):
    # This fetches all FunctionGoals related to this Function
    functional_goals = FunctionGoalSerializer(source='functionsgoals_set', many=True, read_only=True)

    class Meta:
        model = Functions
        fields = ['id', 'function', 'functional_goals']
        
        
class FunctionsEntriesSerializer(serializers.ModelSerializer):
    status= serializers.SlugRelatedField(
        slug_field='status_name',
        queryset=TaskStatus.objects.all()
    )
    class Meta:
        model = FunctionsEntries
        fields = ['id', 'goal',"Creator",'date', 'time', 'status', 'note']
        read_only_fields = ['time', 'Creator']

    # def create(self, validated_data):
        # notes = validated_data.pop('note')
        # # creator = validated_data.get('Creator')
        
        # # If 'note' is a list, create multiple entries
        # if isinstance(notes, list):
        #     entries = [
        #         FunctionsEntries(**validated_data, note=n) 
        #         for n in notes
        #     ]
        #     # bulk_create is highly optimized for performance
        #     return FunctionsEntries.objects.bulk_create(entries)
        
        # # If 'note' is a single string, create normally
        # return FunctionsEntries.objects.create(note=notes, **validated_data)
