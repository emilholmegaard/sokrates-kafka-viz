"""
Smoke tests for visualization generators.

These tests verify that all visualization types can be generated successfully
with a minimal sample dataset.
"""
import json
import os
import shutil
import tempfile
from pathlib import Path
import unittest

from kafka_viz.visualization.factory import visualization_factory
from kafka_viz.visualization.index_generator import IndexGenerator


class VisualizationSmokeTests(unittest.TestCase):
    """Smoke tests for visualization generators."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for outputs
        self.temp_dir = Path(tempfile.mkdtemp())
        
        # Create a minimal sample dataset
        self.sample_data = {
            "services": {
                "service1": {
                    "language": "java",
                    "topics": {
                        "topic1": {
                            "producers": ["service1"],
                            "consumers": ["service2"]
                        }
                    },
                    "schemas": {
                        "schema1": {
                            "type": "avro",
                            "namespace": "com.example"
                        }
                    }
                },
                "service2": {
                    "language": "python",
                    "topics": {
                        "topic1": {
                            "producers": ["service1"],
                            "consumers": ["service2"]
                        },
                        "topic2": {
                            "producers": ["service2"],
                            "consumers": []
                        }
                    },
                    "schemas": {}
                }
            }
        }

    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_all_visualizations(self):
        """Test that all visualizations can be generated."""
        # Get all available generators
        generators = visualization_factory.create_all_generators(exclude=[])
        
        # Track successful visualizations
        successful = []
        
        # Generate each visualization
        for vis_type, generator in generators.items():
            # Create a subdirectory for this visualization
            vis_dir = self.temp_dir / vis_type
            vis_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # Generate the visualization
                generator.generate_output(self.sample_data, vis_dir)
                
                # Get the main output file
                output_file = vis_dir / generator.get_main_output_file()
                
                # Check that the file exists and has content
                self.assertTrue(output_file.exists(), f"Output file for {vis_type} does not exist")
                self.assertTrue(output_file.stat().st_size > 0, f"Output file for {vis_type} is empty")
                
                # Add to successful visualizations
                successful.append({
                    "name": generator.name,
                    "description": generator.description,
                    "path": f"{vis_type}/{generator.get_main_output_file()}",
                    "type": vis_type
                })
                
                print(f"Successfully generated {vis_type} visualization")
                
            except Exception as e:
                self.fail(f"Failed to generate {vis_type} visualization: {e}")
        
        # Test the index generator if we have successful visualizations
        if successful:
            try:
                # Create an index generator
                index_generator = IndexGenerator()
                
                # Generate the index
                index_generator.generate_output(self.sample_data, self.temp_dir, successful)
                
                # Check that the index file exists and has content
                index_file = self.temp_dir / index_generator.get_main_output_file()
                self.assertTrue(index_file.exists(), "Index file does not exist")
                self.assertTrue(index_file.stat().st_size > 0, "Index file is empty")
                
                print("Successfully generated index")
                
            except Exception as e:
                self.fail(f"Failed to generate index: {e}")

    def test_individual_visualizations(self):
        """Test each visualization type individually."""
        # Test each visualization type
        for vis_type in visualization_factory.get_available_generators().keys():
            # Create a generator for this type
            generator = visualization_factory.create_generator(vis_type)
            self.assertIsNotNone(generator, f"Failed to create generator for {vis_type}")
            
            # Create a subdirectory for this visualization
            vis_dir = self.temp_dir / vis_type
            vis_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # Generate the visualization
                generator.generate_output(self.sample_data, vis_dir)
                
                # Get the main output file
                output_file = vis_dir / generator.get_main_output_file()
                
                # Check that the file exists and has content
                self.assertTrue(output_file.exists(), f"Output file for {vis_type} does not exist")
                self.assertTrue(output_file.stat().st_size > 0, f"Output file for {vis_type} is empty")
                
                print(f"Successfully generated {vis_type} visualization")
                
            except Exception as e:
                self.fail(f"Failed to generate {vis_type} visualization: {e}")
                
    def test_generate_subset_visualizations(self):
        """Test generating a subset of visualizations with exclusions."""
        # Get all available generator types
        all_vis_types = list(visualization_factory.get_available_generators().keys())
        
        # Test excluding one generator if there are multiple available
        if len(all_vis_types) > 1:
            # Choose one to exclude
            excluded_type = all_vis_types[0]
            
            # Create generators with exclusion
            generators = visualization_factory.create_all_generators(exclude=[excluded_type])
            
            # Verify the excluded type is not in the generators
            self.assertNotIn(excluded_type, generators.keys(),
                            f"Excluded visualization type {excluded_type} should not be in generators")
            
            # Track successful visualizations
            successful = []
            
            # Generate each visualization
            for vis_type, generator in generators.items():
                # Create a subdirectory for this visualization
                vis_dir = self.temp_dir / vis_type
                vis_dir.mkdir(parents=True, exist_ok=True)
                
                try:
                    # Generate the visualization
                    generator.generate_output(self.sample_data, vis_dir)
                    
                    # Get the main output file
                    output_file = vis_dir / generator.get_main_output_file()
                    
                    # Check that the file exists and has content
                    self.assertTrue(output_file.exists(), f"Output file for {vis_type} does not exist")
                    self.assertTrue(output_file.stat().st_size > 0, f"Output file for {vis_type} is empty")
                    
                    # Add to successful visualizations
                    successful.append({
                        "name": generator.name,
                        "description": generator.description,
                        "path": f"{vis_type}/{generator.get_main_output_file()}",
                        "type": vis_type
                    })
                    
                    print(f"Successfully generated {vis_type} visualization")
                    
                except Exception as e:
                    self.fail(f"Failed to generate {vis_type} visualization: {e}")
            
            # Test the index generator with the subset of visualizations
            if successful:
                try:
                    # Create an index generator
                    index_generator = IndexGenerator()
                    
                    # Generate the index
                    index_generator.generate_output(self.sample_data, self.temp_dir, successful)
                    
                    # Check that the index file exists and has content
                    index_file = self.temp_dir / index_generator.get_main_output_file()
                    self.assertTrue(index_file.exists(), "Index file does not exist")
                    self.assertTrue(index_file.stat().st_size > 0, "Index file is empty")
                    
                    print("Successfully generated index with subset of visualizations")
                    
                except Exception as e:
                    self.fail(f"Failed to generate index: {e}")


if __name__ == "__main__":
    unittest.main()
