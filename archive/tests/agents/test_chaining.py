"""
LangGraph Chaining Agent 테스트

Prompt Chaining 패턴 구현 검증
"""

import sys
import os
import unittest

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.agents.study.langgraph_agent_chaining import LangGraphAgentChaining


class TestLangGraphAgentChaining(unittest.TestCase):
    """LangGraph Chaining Agent 테스트 클래스"""
    
    def setUp(self):
        """테스트 전 설정"""
        self.agent = LangGraphAgentChaining()
    
    def test_agent_initialization(self):
        """Agent 초기화 테스트"""
        self.assertIsNotNone(self.agent.model, "모델이 초기화되어야 합니다")
        self.assertIsNotNone(self.agent.graph, "그래프가 초기화되어야 합니다")
        self.assertTrue(self.agent.is_ready(), "Agent가 준비 상태여야 합니다")
    
    def test_state_structure(self):
        """State 구조 테스트"""
        initial_state = {
            "messages": [],
            "topic": "테스트",
            "joke": "",
            "improved_joke": "",
            "final_joke": "",
            "llm_calls": 0,
            "iteration_count": 0
        }
        
        # State 타입 확인
        self.assertIsInstance(initial_state, dict)
        self.assertIn("topic", initial_state)
        self.assertIn("joke", initial_state)
        self.assertIn("improved_joke", initial_state)
        self.assertIn("final_joke", initial_state)
    
    def test_generate_joke_node(self):
        """generate_joke 노드 테스트"""
        state = {
            "messages": [],
            "topic": "고양이",
            "joke": "",
            "improved_joke": "",
            "final_joke": "",
            "llm_calls": 0,
            "iteration_count": 0
        }
        
        result = self.agent.generate_joke(state)
        
        # 결과 검증
        self.assertIn("joke", result)
        self.assertIn("llm_calls", result)
        self.assertGreater(result["llm_calls"], 0)
        self.assertGreater(len(result["joke"]), 0)
    
    def test_check_punchline_gate_function(self):
        """check_punchline Gate function 테스트"""
        # Punchline이 있는 경우
        state_with_punchline = {
            "joke": "왜 고양이는 컴퓨터를 쓸까? 마우스를 좋아하니까!"
        }
        result = self.agent.check_punchline(state_with_punchline)
        self.assertEqual(result, "Pass")
        
        # Punchline이 없는 경우
        state_without_punchline = {
            "joke": "고양이는 귀여운 동물입니다"
        }
        result = self.agent.check_punchline(state_without_punchline)
        self.assertEqual(result, "Fail")
    
    def test_graph_flow(self):
        """그래프 흐름 테스트"""
        # 그래프 노드 확인
        self.assertIn("generate_joke", self.agent.graph.nodes)
        self.assertIn("improve_joke", self.agent.graph.nodes)
        self.assertIn("polish_joke", self.agent.graph.nodes)
    
    def test_generate_response(self):
        """응답 생성 테스트"""
        topic = "고양이"
        response = self.agent.generate_response(topic)
        
        # 응답 검증
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        self.assertIn(topic, response)
    
    def test_chaining_workflow(self):
        """전체 Chaining 워크플로우 테스트"""
        # 간단한 주제로 테스트
        topic = "고양이"
        
        initial_state = {
            "messages": [],
            "topic": topic,
            "joke": "",
            "improved_joke": "",
            "final_joke": "",
            "llm_calls": 0,
            "iteration_count": 0
        }
        
        # 그래프 실행
        result = self.agent.graph.invoke(initial_state)
        
        # 결과 검증
        self.assertIn("topic", result)
        self.assertEqual(result["topic"], topic)
        self.assertGreater(result["llm_calls"], 0)
    
    def test_streaming(self):
        """스트리밍 테스트"""
        topic = "고양이"
        
        initial_state = {
            "messages": [],
            "topic": topic,
            "joke": "",
            "improved_joke": "",
            "final_joke": "",
            "llm_calls": 0,
            "iteration_count": 0
        }
        
        # 스트리밍 실행
        chunks = list(self.agent.graph.stream(initial_state))
        
        # 결과 검증
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertIsInstance(chunk, dict)
    
    def test_agent_info(self):
        """Agent 정보 테스트"""
        info = self.agent.get_info()
        
        # 정보 검증
        self.assertIn("type", info)
        self.assertIn("architecture", info)
        self.assertIn("nodes", info)
        self.assertIn("flow", info)
        self.assertEqual(info["type"], "LangGraph Chaining Agent")
    
    def test_error_handling(self):
        """에러 처리 테스트"""
        # 빈 쿼리로 테스트
        response = self.agent.generate_response("")
        
        # 에러 응답 검증
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)


class TestChainingIntegration(unittest.TestCase):
    """통합 테스트"""
    
    def test_full_workflow(self):
        """전체 워크플로우 통합 테스트"""
        agent = LangGraphAgentChaining()
        
        # 여러 주제로 테스트
        topics = ["고양이", "프로그래머", "코딩"]
        
        for topic in topics:
            with self.subTest(topic=topic):
                response = agent.generate_response(topic)
                self.assertIsInstance(response, str)
                self.assertGreater(len(response), 0)


if __name__ == "__main__":
    # 테스트 실행
    unittest.main(verbosity=2)

