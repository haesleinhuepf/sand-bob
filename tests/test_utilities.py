"""
Tests for the utilities module.
"""

import pytest
import numpy as np
from sand_bob._utilities import find_most_common_indices


class TestFindMostCommonIndices:
    """Test cases for find_most_common_indices function."""
    
    def test_basic_functionality(self):
        """Test basic functionality with numbers."""
        # Test case: [1,2,2,1,1] should return [0,3,4]
        result = find_most_common_indices([1, 2, 2, 1, 1])
        expected = [0, 3, 4]
        assert result == expected
    
    def test_mixed_types(self):
        """Test with mixed types."""
        # Test case: ['a', 'b', 'a', 1, 2, 1] should return [0, 2, 3, 5]
        result = find_most_common_indices(['a', 'b', 'a', 1, 2, 1])
        expected = [0, 2, 3, 5]
        assert result == expected
    
    def test_numpy_arrays(self):
        """Test with numpy arrays."""
        arr1 = np.array([1, 2, 3])
        arr2 = np.array([4, 5, 6])
        arr3 = np.array([1, 2, 3])  # Same as arr1
        
        result = find_most_common_indices([arr1, arr2, arr3, "string", arr1])
        expected = [0, 2, 4]  # Indices of arr1 and arr3 (which are the same)
        assert result == expected
    
    def test_lists_and_tuples(self):
        """Test with lists and tuples."""
        list1 = [1, 2, 3]
        list2 = [4, 5, 6]
        tuple1 = (1, 2, 3)  # Same content as list1
        
        result = find_most_common_indices([list1, list2, tuple1, "string", list1])
        expected = [0, 2, 4]  # Indices of list1 and tuple1 (same content)
        assert result == expected
    
    def test_dictionaries(self):
        """Test with dictionaries."""
        dict1 = {'a': 1, 'b': 2}
        dict2 = {'c': 3, 'd': 4}
        dict3 = {'b': 2, 'a': 1}  # Same as dict1 but different order
        
        result = find_most_common_indices([dict1, dict2, dict3, 42, dict1])
        expected = [0, 2, 4]  # Indices of dict1 and dict3 (same content)
        assert result == expected
    
    def test_empty_list(self):
        """Test with empty list."""
        result = find_most_common_indices([])
        expected = []
        assert result == expected
    
    def test_single_item(self):
        """Test with single item."""
        result = find_most_common_indices([42])
        expected = [0]
        assert result == expected
    
    def test_all_unique_items(self):
        """Test with all unique items."""
        result = find_most_common_indices([1, 2, 3, 4, 5])
        expected = [0, 1, 2, 3, 4]  # All items are equally common (count=1)
        assert result == expected
    
    def test_booleans(self):
        """Test with boolean values."""
        result = find_most_common_indices([True, False, True, True, False])
        expected = [0, 2, 3]  # Indices of True (appears 3 times)
        assert result == expected
    
    def test_floats_and_ints(self):
        """Test with mixed float and int values."""
        result = find_most_common_indices([1, 1.0, 2, 1, 2.0])
        expected = [0, 1, 3, 4]  # Indices of 1, 1.0, 2, 2.0 (all appear once)
        assert result == expected
    
    def test_large_arrays(self):
        """Test with large numpy arrays that should use hashing."""
        arr1 = np.random.rand(100, 100)  # Large array
        arr2 = np.random.rand(100, 100)  # Different large array
        arr3 = np.random.rand(100, 100)  # Another different array
        
        result = find_most_common_indices([arr1, arr2, arr1, "string", arr3])
        expected = [0, 2]  # Indices of arr1 (appears twice)
        assert result == expected
    
    def test_nested_structures(self):
        """Test with nested lists and tuples."""
        nested1 = [[1, 2], [3, 4]]
        nested2 = [[1, 2], [3, 4]]  # Same as nested1
        nested3 = [[5, 6], [7, 8]]  # Different
        
        result = find_most_common_indices([nested1, nested2, nested3, 42])
        expected = [0, 1]  # Indices of nested1 and nested2 (same content)
        assert result == expected
    
    def test_complex_dictionaries(self):
        """Test with complex nested dictionaries."""
        dict1 = {'a': {'x': 1, 'y': 2}, 'b': [1, 2, 3]}
        dict2 = {'b': [1, 2, 3], 'a': {'y': 2, 'x': 1}}  # Same as dict1 but different order
        dict3 = {'c': 3, 'd': 4}  # Different
        
        result = find_most_common_indices([dict1, dict2, dict3, "string"])
        expected = [0, 1]  # Indices of dict1 and dict2 (same content)
        assert result == expected
    
    def test_edge_case_none_values(self):
        """Test with None values."""
        result = find_most_common_indices([None, 1, None, 2, None])
        expected = [0, 2, 4]  # Indices of None (appears 3 times)
        assert result == expected
    
    def test_mixed_none_and_other_types(self):
        """Test with None mixed with other types."""
        result = find_most_common_indices([None, "hello", None, 42, "hello"])
        expected = [1, 4]  # Indices of "hello" (appears twice, more than None)
        assert result == expected
