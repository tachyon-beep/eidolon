import { createRouter, createWebHistory } from 'vue-router'
import ExploreView from '../views/ExploreView.vue'
import CodeView from '../views/CodeView.vue'
import PlanView from '../views/PlanView.vue'

const routes = [
  {
    path: '/',
    redirect: '/explore'
  },
  {
    path: '/explore',
    name: 'Explore',
    component: ExploreView
  },
  {
    path: '/code',
    name: 'Code',
    component: CodeView
  },
  {
    path: '/plan',
    name: 'Plan',
    component: PlanView
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
